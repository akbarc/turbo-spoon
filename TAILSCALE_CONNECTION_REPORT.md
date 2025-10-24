# Tailscale SQL Server Connection Attempt - Complete Report

## Environment Details

### Client Machine (MacBook)
- Hostname: MacBook-Pro-5.local
- Location: Remote (attempting to connect via Tailscale)
- Python Version: 3.11.4
- pymssql Version: 2.3.7
- Installed SQL Tools: freetds, mssql-tools, mssql-tools18
- Tailscale IP of target: 100.84.221.9

### Office Computer (Windows)
- Computer Name: DESKTOP-SRVMC6B
- Windows Version: 10.0.19045.6332
- Network IP: 10.1.10.105
- Tailscale IP: 100.84.221.9
- Tailscale Status: Running on both machines

### SQL Server Infrastructure
Two SQL Server instances identified:

1. **SOSERVER (Default Instance)**
   - Version: SQL Server 10.50.2500 (SQL Server 2008 R2)
   - Port: 1433
   - Databases: GAWDB, SAMPLE, master, model, msdb, tempdb
   - Logins: amchranya (SQL_LOGIN), sa (SQL_LOGIN), RMS_ReadOnly (SQL_LOGIN)
   - Authentication Mode: Mixed Mode (SQL + Windows)

2. **SOSERVER\SQLEXPRESS**
   - Version: SQL Server 9.0.5000 (SQL Server 2005)
   - Port: 49169
   - Databases: master, model, msdb, tempdb, security
   - Logins: sa
   - GAWDB database: NOT PRESENT

## Connection Tests Performed

### Test 1: Initial Tailscale Connectivity
```
ping 100.84.221.9
Result: SUCCESS - 4 packets transmitted, 4 received, 0.0% packet loss
RTT: min/avg/max = 1.898/12.457/43.631 ms
```

### Test 2: Port Accessibility Tests
```
nc -zv 100.84.221.9 1433
Result: SUCCESS - Connection to 100.84.221.9 port 1433 [tcp/ms-sql-s] succeeded

nc -zv 100.84.221.9 49169
Result: TIMEOUT - Port not accessible
```

### Test 3: Database Connection Configuration Found
File: `/Users/akbarchranya/georgiadashboard/.env`
- Original: DB_SERVER=10.1.10.105
- Modified to: DB_SERVER=100.84.221.9
- DB_PORT=1433
- DB_USERNAME values tried: amchranya, georgia_app, sa
- DB_PASSWORD values tried: 2000Akbar!, Georgia2024!, Tech7World, Tech7World!, tech7world!
- DB_DATABASE=GAWDB
- TDS_VERSION=7.0

### Test 4: Python pymssql Connection Attempts

#### Configuration 1: Tailscale IP with amchranya
```python
server='100.84.221.9', user='amchranya', password='2000Akbar!', database='GAWDB'
```
- With TDS 7.0: Error 18456 - Login failed
- With TDS 7.1: Error 20002 - TDS server connection failed
- With TDS 7.2: Error 20002 - TDS server connection failed
- With TDS 8.0: Error 20017 - TDS protocol error
- Without TDS specified: Error 20017

#### Configuration 2: Office IP from remote
```python
server='10.1.10.105', user='amchranya', password='2000Akbar!', database='GAWDB'
```
Result: Error 20009 - Unable to connect (timeout) - Expected, not on office network

#### Configuration 3: Computer name
```python
server='DESKTOP-SRVMC6B', user='amchranya', password='2000Akbar!'
```
Result: Error 18456 - Login failed

#### Configuration 4: SQL Express instance
```python
server='100.84.221.9\\SQLEXPRESS', port=49169
```
Result: Error 20009 - Unable to connect

#### Configuration 5: Master database instead of GAWDB
```python
server='100.84.221.9', database='master', user='amchranya'
```
Result: Error 18456 - Login failed

### Test 5: sqlcmd Command Line Tests
```bash
sqlcmd -S 100.84.221.9 -U amchranya -P '2000Akbar!' -d GAWDB
```
Result: SSL Provider error - unsupported protocol

```bash
sqlcmd -S 100.84.221.9 -U amchranya -P '2000Akbar!' -d GAWDB -C
```
Result: SSL Provider error (even with -C flag to bypass SSL)

### Test 6: FreeTDS Configuration Tests

Created `~/.freetds.conf`:
```
[global]
    tds version = 7.0
[GeorgiaDashboard]
    host = 100.84.221.9
    port = 1433
    tds version = 7.0
```

```bash
tsql -S GeorgiaDashboard -U amchranya -P '2000Akbar!'
```
Result: Msg 18456 - Login failed for user 'amchranya'
Server identification: DESKTOP-SRVMC6B returned in error

### Test 7: SQL Server Configuration Checks (via SSMS)

#### Windows Authentication Query Results:
```sql
SELECT SERVERPROPERTY('IsIntegratedSecurityOnly')
```
Result: 0 (Mixed Mode authentication confirmed)

```sql
SELECT name, is_disabled, type_desc FROM sys.server_principals WHERE type = 'S'
```
Result: amchranya (0 - not disabled), sa (0 - not disabled), RMS_ReadOnly (0)

```sql
EXEC xp_cmdshell 'netstat -an | findstr :1433'
```
Result: Permission denied (user lacks admin rights)

Command Prompt (on office computer):
```cmd
netstat -an | findstr :1433
```
Result:
- TCP 0.0.0.0:1433 LISTENING (listening on all interfaces)
- TCP [::]:1433 LISTENING

### Test 8: SQL Commands Executed
```sql
GRANT CONNECT SQL TO amchranya
```
Result: Command completed (on SOSERVER instance)

```sql
ALTER LOGIN amchranya WITH CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF
```
Result: Error 15151 - Cannot alter login (permission denied)

```sql
CREATE LOGIN tailscale_test WITH PASSWORD = 'Test123!'
```
Result: Not executed due to lack of permissions

```sql
CREATE LOGIN remote_user WITH PASSWORD = 'Remote123!'
```
Result: Not confirmed if executed

### Test 9: Network Socket Tests
```python
socket.connect_ex(('100.84.221.9', 1433))
```
Result: 0 (SUCCESS - port is open)

```python
socket.connect_ex(('10.1.10.105', 1433))
```
Result: Connection failed (not on office network)

## Error Patterns Identified

1. **Error 20002/20009**: TDS connection failure - Initial connection attempts
2. **Error 18456**: Login failed - After TDS 7.0 configuration
3. **SSL Provider errors**: Modern SQL tools incompatible with SQL Server 2008 R2

## Key Findings

1. **Tailscale networking**: Functional - ping successful, port 1433 accessible
2. **SQL Server listening**: On 0.0.0.0:1433 (all interfaces)
3. **Authentication mode**: Mixed (SQL + Windows) confirmed
4. **Login exists**: amchranya present in sys.server_principals
5. **Password**: 2000Akbar! confirmed working in SSMS locally
6. **Connection result**: All SQL authentication attempts from Tailscale IP failed with login error
7. **Error progression**: Changed from connection failure (20002) to authentication failure (18456) after TDS 7.0
8. **Server identification**: SQL Server responds with DESKTOP-SRVMC6B hostname in error messages

## Configuration Files Modified

1. `/Users/akbarchranya/georgiadashboard/.env`
   - Changed DB_SERVER from 10.1.10.105 to 100.84.221.9
   - Changed DB_USERNAME between amchranya, georgia_app, sa
   - Changed DB_PASSWORD between multiple values

2. `/Users/akbarchranya/georgiadashboard/database_pymssql.py`
   - Line 52: Modified default server from 'localhost' to '100.84.221.9' then back to '10.1.10.105'

3. `~/.freetds.conf`
   - Created with TDS 7.0 and 7.2 configurations

## Constraints Encountered

1. SQL Server Configuration Manager: WMI error - "Cannot connect to WMI provider"
2. Admin access: Not available on office computer
3. SQL Express instance: Port 49169 not accessible via Tailscale
4. Registry access: Not available without admin rights

## Final State

- Tailscale network: Functional
- Port 1433: Accessible via Tailscale
- SQL Server: Responding but rejecting SQL authentication from Tailscale IP
- Error type: Authentication failure (18456) not network failure
- Working configuration: Unknown for remote access
- Office local access: Functional with 10.1.10.105