# Microsoft RMS Receipt Template Documentation

## Template Information
- **Template ID**: 1
- **Title**: Full Page Receipt
- **Description**: Full Page Receipt
- **Database Location**: 
  - Server: 10.1.10.105
  - Database: GAWDB
  - Table: dbo.Receipt
  - Column: TemplateSale

## Transaction Types Supported

The template includes conditional formatting for the following transaction types:

- **transactionSales** - Regular sales transactions
- **transactionAccountPayment** - Account payment transactions  
- **transactionDrop** - Cash drop transactions
- **transactionPayOut** - Payout transactions
- **transactionBackOrder** - Back order transactions
- **transactionWorkOrder** - Work order transactions
- **transactionQuote** - Quote transactions
- **transactionLayaway** - Layaway transactions
- **transactionAbortedTransaction** - Void/cancelled transactions

## XML Structure Overview

The template uses Microsoft RMS XML format with the following key elements:

- `<SET>` - Variable definitions (paper size, margins, fonts, etc.)
- `<TABLE>` - Layout tables with columns and rows
- `<COLUMNHEADER>` - Column definitions with alignment and width
- `<IF><CONDITION>` - Conditional logic based on transaction type
- `<FOR each>` - Loops for items, taxes, etc.
- `<TEXT>` - Static and dynamic text content
- `<ALIGNMENT>` - Text alignment (`&lt;` = left, `&gt;` = right, `^` = center)
- `<WIDTH>` - Column widths (often as percentage of PageWidth)

## Paper Settings

- **Paper Width**: 8.5 inches
- **Paper Height**: 11.0 inches  
- **Margins**: 0.3 inches (left, right, top, bottom)
- **Format**: Full-page business receipt (not thermal)

## Complete XML Template

```xml
<XML>
	<PROPERTIES>
		<DESCRIPTION>GEORGIA WHOLESALE</DESCRIPTION>
		<AUTHOR>       POS Unlimited, Microsoft Corporation     </AUTHOR>
		<VERSION>      Version 1.05                 </VERSION>
	</PROPERTIES>
	<!--
   ===========================
   Attributes
   ===========================
-->
	<SET name="ReceiptCount" custom="true" description="Receipt Count" type="vbLong">1</SET>
	<SET name="PaperWidth" custom="true" description="Paper Width" type="vbdouble">        8.5   </SET>
	<SET name="PaperHeight" custom="true" description="Paper Height" type="vbdouble">      11.00 </SET>
	<SET name="MarginLeft" custom="true" description="Margin Left" type="vbdouble">.3</SET>
	<SET name="MarginRight" custom="true" description="Margin Right" type="vbdouble">.3</SET>
	<SET name="MarginTop" custom="true" description="Margin Top" type="vbdouble">.3</SET>
	<SET name="MarginBottom" custom="true" description="Margin Bottom" type="vbdouble">.3</SET>
	<SET name="HeaderHeight" custom="true" description="Header Height" type="vbdouble">3.5</SET>
	<SET name="FooterHeight" custom="true" description="Footer Height" type="vbdouble">    2.2    </SET>
	<SET name="CommentLine1" custom="true" description="Comment Line 1" type="vbString">"THANK YOU FOR SHOPPING WITH US"</SET>
	<SET name="CommentLine2" custom="true" description="Comment Line 2" type="vbString">"PLEASE BE SURE AND CHECK YOUR ITEMS"</SET>
	<SET name="CommentLine3" custom="true" description="Comment Line 3" type="vbString">"WE ARE NOT RESPONSIBLE FOR SHORT OR DAMAGED GOODS ONCE THE TRANSACTION IS COMPLETED"</SET>
	<SET name="CommentLine4" custom="true" description="Comment Line 4" type="vbString">
	</SET>
	<SET name="CommentLine5" custom="true" description="Comment Line 5" type="vbString"></SET>
	<SET name="TXTTobaccoLic" custom="true" description="TXT Tobacco Lic" type="vbString"> "TOBACCO LIC#"</SET>
	<SET name="TobaccoLic" custom="true" description="Tobacco Lic" type="vbString"> "0046812"</SET>
	<SET name="TXTResaleCert" custom="true" description="TXT Resale Cert" type="vbString"> "RESALE CERT#"</SET>
	<SET name="ResaleCert" custom="true" description="Resale Cert" type="vbString"> "308-045115"</SET>
	<SET name="TXTFEIN" custom="true" description="TXT FEIN" type="vbString"> "FEIN #"</SET>
	<SET name="FEIN" custom="true" description="FEIN" type="vbString"> "46-0768846"</SET>
	<SET name="TXTStateTaxID" custom="true" description="TXT StateTax ID" type="vbString"> "STATE TAX ID#"</SET>
	<SET name="StateTaxID" custom="true" description="StateTax ID" type="vbString"> "20221911149"</SET>
	<SET name="CompanyAddInfo1" custom="true" description="Company Add Info 1" type="vbString"> "WE DO MSA REPORTING"</SET>
	<SET name="CompanyAddInfo2" custom="true" description="Company Add Info 2" type="vbString">"OUR MSA DID# 17000028"</SET>
	<SET name="TXTCustomerID" custom="true" description="TXT Customer ID" type="vbString"> "I.D."</SET>
	<SET name="TXTCustomerTabaccoLic" custom="true" description="TXT Customer Tabacco Lic" type="vbString">"TOBACCO LIC#"</SET>
	<SET name="ShowBComments" custom="true" description="Show BComments" type="vbBoolean">                 True  </SET>
	<SET name="BCommentLine1" custom="true" description="BComment Line 1" type="vbString">      "X_____________________________________________"</SET>
	<SET name="BCommentLine2" custom="true" description="BComment Line 2" type="vbString">      "ALL SALES ARE FINAL, NO RETURN NO EXCHANGE"</SET>
	<SET name="BCommentLine3" custom="true" description="BComment Line 3" type="vbString">"INTERST AND/OR  LATE FEE WOULD BE CHARGED ON ALL PAST DUE INVOICE"</SET>
	<SET name="LogoFilename" custom="true" description="Logo Filename" type="vbString"></SET>
	<SET name="ShowStoreInfo" custom="true" description="Show Store Name/Address" type="vbBoolean">     True  </SET>
	<SET name="ShowCustomerAddress" custom="true" description="Show Customer Address" type="vbBoolean">   True  </SET>
	<SET name="ShowLineDiscounts" custom="true" description="Show Line Discounts" type="vbBoolean">      False  </SET>
	<SET name="ShowTotalQuantity" custom="true" description="Show Total Quantity" type="vbBoolean">  True  </SET>
	<SET name="ShowTotalSaving" custom="true" description="Show Total Saving" type="vbBoolean">  True  </SET>
	<SET name="ShowSalesTax" custom="true" description="Show Sales Tax" type="vbBoolean">            False  </SET>
	<SET name="ShowTaxDetails" custom="true" description="Show Tax Details" type="vbBoolean">            False  </SET>
	<SET name="ShowBarcode" custom="true" description="Show Barcode" type="vbBoolean">TRUE</SET>
	<SET name="ShowLogo" custom="true" description="Show Logo" type="vbBoolean">                         True  </SET>
	<SET name="ShowComments" custom="true" description="Show Comments" type="vbBoolean">                 True  </SET>
	<SET name="ShowDuplicate" custom="true" description="Show Duplicate" type="vbBoolean">  True  </SET>
	<SET name="ShowPreBalance" custom="true" description="Show Customer Previous Account Balances" type="vbBoolean">TRUE</SET>
	<SET name="ShowAccountBalance" custom="true" description="Show Customer Account Balances" type="vbBoolean">  True  </SET>
	<SET name="MaskCreditCard" custom="true" description="Mask Credit Card Number" type="vbBoolean">  True  </SET>
	<SET name="LineColor" custom="true" description="Line Color" type="vbString">                          vbYellow  </SET>
	<SET name="ExciseTaxBegin" custom="true" description="Excise Tax Begin" type="vbString">"Georgia Excise Tax Paid"</SET>
	<SET name="ExciseTaxEnd" custom="true" description="Excise Tax End" type="vbString">"Included in This Invoice"</SET>
	<!--
   ===========================
   Variable Declarations
   ===========================
-->
	<SET name="PageWidth" type="vbdouble">  PaperWidth - MarginLeft - MarginRight  </SET>
	<SET name="PageHeight" type="vbdouble">  PaperHeight - MarginTop - MarginBottom - HeaderHeight - FooterHeight</SET>
	<SET name="NewAccountBalance" type="vbcurrency">  0 </SET>
	<SET name="TotalExciseTax" type="vbcurrency"> 0 </SET>
	<SET name="UnitPrice" type="vbcurrency"> 0 </SET>
	<SET name="NewLineNo" type="vbLong">  0 </SET>
	<!--
   ===========================
   Page Settings
   ===========================
-->
	<MARGIN>
		<COPIES>    ReceiptCount    </COPIES>
		<TOP>       MarginTop + HeaderHeight      </TOP>
		<BOTTOM>    MarginBottom + FooterHeight   </BOTTOM>
		<LEFT>      MarginLeft      </LEFT>
		<RIGHT>     MarginRight     </RIGHT>
		<ORIENTATION>orPortrait</ORIENTATION>
	</MARGIN>
	<!--
   ===========================
   Font Declarations
   ===========================
-->
	<FONT name="">
		<NAME>      "Arial"        </NAME>
		<SIZE>      10              </SIZE>
		<BOLD>      False          </BOLD>
		<UNDERLINE> False          </UNDERLINE>
		<ITALIC>    False          </ITALIC>
		<COLOR>     vbBlack        </COLOR>
	</FONT>
	<FONT name="Small">
		<NAME>      "Arial"        </NAME>
		<SIZE>      10              </SIZE>
		<BOLD>      False          </BOLD>
		<UNDERLINE> False          </UNDERLINE>
		<ITALIC>    False          </ITALIC>
		<COLOR>     vbBlack        </COLOR>
	</FONT>
	<FONT name="Large">
		<NAME>      "Arial"        </NAME>
		<SIZE>24</SIZE>
		<BOLD>      True           </BOLD>
		<UNDERLINE> False          </UNDERLINE>
		<ITALIC>    False          </ITALIC>
		<COLOR>     vbBlack        </COLOR>
	</FONT>
	<FONT name="Huge">
		<NAME>      "Arial"        </NAME>
		<SIZE>      36             </SIZE>
		<BOLD>      True           </BOLD>
		<UNDERLINE> False          </UNDERLINE>
		<ITALIC>    False          </ITALIC>
		<COLOR>     vbRed        </COLOR>
	</FONT>
	<!--
   ===========================
   Header
   ===========================
-->
	<SUB name="DrawHeader">
		<TABLE>
			<TOP> MarginTop </TOP>
			<FONT> "Large" </FONT>
			<BORDER> tbNone </BORDER>
			<COLUMNHEADER>
				<ALIGNMENT> "&lt;~" </ALIGNMENT>
				<IF>
					<CONDITION> ShowLogo </CONDITION>
					<THEN>
						<WIDTH>     PageWidth * 0.20     </WIDTH>
					</THEN>
					<ELSE>
						<WIDTH>     0.001    </WIDTH>
					</ELSE>
				</IF>
			</COLUMNHEADER>
			<COLUMNHEADER>
				<ALIGNMENT> "&lt;~"            </ALIGNMENT>
				<IF><CONDITION> ShowLogo </CONDITION>
					<THEN><WIDTH>     PageWidth * 0.50     </WIDTH></THEN>
					<ELSE><WIDTH>     PageWidth * 0.70     </WIDTH></ELSE>
				</IF>
				<IF><CONDITION> ShowStoreInfo </CONDITION>
					<THEN><TEXT> Store.Name </TEXT></THEN>
					<ELSE><TEXT> "" </TEXT></ELSE>
				</IF>
			</COLUMNHEADER>
			<COLUMNHEADER>
				<ALIGNMENT> "&gt;~"            </ALIGNMENT>
				<WIDTH>     PageWidth * 0.30     </WIDTH>
				<TEXT>      Transaction.ReceiptTransactionName </TEXT>
			</COLUMNHEADER>
		</TABLE>
		<!--
   ===========================
   Store Address & trans. info
   ===========================
-->
		<TABLE>
			<BORDER> tbNone </BORDER>
			<COLUMNHEADER>
				<ALIGNMENT> "&lt;~" </ALIGNMENT>
				<WIDTH> PageWidth * 0.15 </WIDTH>
			</COLUMNHEADER>
			<COLUMNHEADER>
				<ALIGNMENT> "&lt;~" </ALIGNMENT>
				<WIDTH> PageWidth * 0.15 </WIDTH>
			</COLUMNHEADER>
			<COLUMNHEADER>
				<ALIGNMENT> "&lt;~" </ALIGNMENT>
				<WIDTH> PageWidth * 0.40 </WIDTH>
			</COLUMNHEADER>
			<COLUMNHEADER>
				<ALIGNMENT> "&lt;~" </ALIGNMENT>
				<WIDTH> PageWidth * 0.15 </WIDTH>
			</COLUMNHEADER>
			<COLUMNHEADER>
				<ALIGNMENT> "&lt;~" </ALIGNMENT>
				<WIDTH> PageWidth * 0.15 </WIDTH>
			</COLUMNHEADER>
			<ROW> "||" Store.Address1 " " Store.Address2 "|" TXTTobaccoLic "|" TobaccoLic </ROW>
			<ROW> "||" Store.CityStateZip "|" TXTResaleCert "|" ResaleCert </ROW>
			<ROW> "||Phone: " Store.Phone  "|" TXTFEIN "|" FEIN</ROW>
			<ROW> "||Fax    : " Store.Fax  "|" TXTStateTaxID "|" StateTaxID</ROW>
			<ROW newline="true"></ROW>
			<ROW> "Date|" Transaction.Date "|" CompanyAddInfo1 "|Page|\p of \t"  </ROW>
			<ROW> "Time|" Transaction.Time "|" CompanyAddInfo2 "|" Transaction.ReceiptTransactionNumberCaption "|" Transaction.ReceiptTransactionNumber </ROW>
			<ROW> "Cashier|" Cashier.Number "||Account #|" Customer.AccountNumber </ROW>
			<ROW> "Register #|" Register.Number "||" TXTCustomerID "|" Customer.TaxNumber </ROW>
			<ROW> "|||" TXTCustomerTabaccoLic "|" Customer.CustomText2 </ROW>
		</TABLE>
		<!--
			<IF><CONDITION> ShowStoreInfo </CONDITION>
				<THEN>
					<ROW> "|" Store.CityStateZip "|" Transaction.ReceiptTransactionNumberCaption ":|" Transaction.ReceiptTransactionNumber </ROW>
					<ROW> "|Phone:" Store.Phone "|Account #:|" Customer.AccountNumber </ROW>
					<ROW> "|Fax    :" Store.Fax  "|Page:|\p of \t" </ROW>
				</THEN>
				<ELSE>
					<ROW> "||" Transaction.ReceiptTransactionNumberCaption ":|" Transaction.ReceiptTransactionNumber </ROW>
					<ROW> "||Account #:|" Customer.AccountNumber </ROW>
					<ROW> "||Page:|\p of \t" </ROW>
				</ELSE>
			</IF>
			<ROW> "||Date:|" Transaction.Date </ROW>
			<ROW> "||Time:|" Transaction.Time </ROW>
			<ROW> "||Cashier:|" Cashier.Number </ROW>
			<ROW> "||Register #:|" Register.Number </ROW>
			<ROW> "||Register #:|" Register.Number </ROW>
			<ROW></ROW>
   ===========================
   Bill To & Ship To
   ===========================
-->
		<TABLE>
			<BORDER> tbNone </BORDER>
			<!--
			<COLUMNHEADER>
				<ALIGNMENT> "&lt;" </ALIGNMENT>
				<WIDTH> PageWidth * 0.10 </WIDTH>
				<TEXT> "Bill To:" </TEXT>
			</COLUMNHEADER>
				<TEXT skipblank="true" newline="true"> Customer.Name </TEXT>
-->
			<COLUMNHEADER>
				<ALIGNMENT> "&lt;" </ALIGNMENT>
				<WIDTH> PageWidth * 0.50 </WIDTH>
				<TEXT newline="true"> "Bill To:" </TEXT>
				<TEXT skipblank="true" newline="true"> Customer.HomeAddress.Company </TEXT>
				<TEXT skipblank="true" newline="true"> Customer.HomeAddress.StreetAddress</TEXT>
				<TEXT skipblank="true" newline="true"> Customer.HomeAddress.StreetAddress2</TEXT>
				<TEXT skipblank="true" newline="true"> Customer.HomeAddress.CityStateZip </TEXT>
				<TEXT skipblank="true" newline="true"> Customer.HomeAddress.PhoneNumber "  FAX:" Customer.HomeAddress.FaxNumber</TEXT>
			</COLUMNHEADER>
			<!--
			<COLUMNHEADER>
				<ALIGNMENT> "&lt;" </ALIGNMENT>
				<WIDTH> PageWidth * 0.10 </WIDTH>
				<TEXT> "Ship To:" </TEXT>
			</COLUMNHEADER>
				<TEXT skipblank="true" newline="true"> Customer.ShipToAddress.Name </TEXT>
-->
			<COLUMNHEADER>
				<ALIGNMENT> "&lt;" </ALIGNMENT>
				<WIDTH> PageWidth * 0.50 </WIDTH>
				<TEXT newline="true"> "Ship To:" </TEXT>
				<TEXT skipblank="true" newline="true"> Customer.ShipToAddress.Company </TEXT>
				<TEXT skipblank="true" newline="true"> Customer.ShipToAddress.StreetAddress</TEXT>
				<TEXT skipblank="true" newline="true"> Customer.ShipToAddress.StreetAddress2</TEXT>
				<TEXT skipblank="true" newline="true"> Customer.ShipToAddress.CityStateZip </TEXT>
				<TEXT skipblank="true" newline="true"> Customer.ShipToAddress.PhoneNumber "  FAX:" Customer.ShipToAddress.FaxNumber</TEXT>
			</COLUMNHEADER>
		</TABLE>
		<!--
		<TABLE>
			<BORDER> tbNone </BORDER>
			<COLUMNHEADER>
				<ALIGNMENT> "&lt;~" </ALIGNMENT>
				<WIDTH> PageWidth * 0.15 </WIDTH>
				<TEXT> "" </TEXT>
			</COLUMNHEADER>
			<COLUMNHEADER>
				<ALIGNMENT> "&lt;~" </ALIGNMENT>
				<WIDTH> PageWidth * 0.55 </WIDTH>
				<TEXT> "" </TEXT>
			</COLUMNHEADER>
			<COLUMNHEADER>
				<ALIGNMENT> "&lt;~" </ALIGNMENT>
				<WIDTH> PageWidth * 0.30 </WIDTH>
				<TEXT> "" </TEXT>
			</COLUMNHEADER>
                        <IF>
                        <CONDITION> Customer.PreviousAccountBalance &lt;&gt; 0 </CONDITION>
                        <THEN>
    			<IF>
    				<CONDITION>Len(Transaction.Comment) | Customer.PreviousAccountBalance = 0</CONDITION>
    				<THEN>
    					<ROW>"Reference:|" Transaction.ReferenceNumber "|"</ROW>
    				</THEN>
    			</IF>
    			<IF>
    				<CONDITION>Len(Transaction.Comment) | Customer.PreviousAccountBalance = 0</CONDITION>
    				<THEN>
    					<ROW>"Comment:|" Transaction.Comment "|" </ROW>
    				</THEN>
    			</IF>
                        </THEN>
                        <ELSE>
    			<IF>
    				<CONDITION>Len(Transaction.Comment) | Customer.PreviousAccountBalance &lt;&gt; 0</CONDITION>
    				<THEN>
    					<ROW>"Reference:|" Transaction.ReferenceNumber "|"</ROW>
    				</THEN>
    			</IF>
    			<IF>
    				<CONDITION>Len(Transaction.Comment) | Customer.PreviousAccountBalance &lt;&gt; 0</CONDITION>
    				<THEN>
    					<ROW>"Comment:|" Transaction.Comment "|Total A/R Balance:  " Customer.PreviousAccountBalance</ROW>
    				</THEN>
    			</IF>
                        </ELSE>
                        </IF>

		</TABLE>
-->
		<TABLE>
			<BORDER> tbNone </BORDER>
			<COLUMNHEADER>
				<ALIGNMENT> "&lt;~" </ALIGNMENT>
				<WIDTH> PageWidth * 0.15 </WIDTH>
				<TEXT> "" </TEXT>
			</COLUMNHEADER>
			<COLUMNHEADER>
				<ALIGNMENT> "&lt;~" </ALIGNMENT>
				<WIDTH> PageWidth * 0.85 </WIDTH>
				<TEXT> "" </TEXT>
			</COLUMNHEADER>
			<IF>
				<CONDITION>Len(Transaction.Comment)</CONDITION>
				<THEN>
					<ROW>"Reference:|" Transaction.ReferenceNumber </ROW>
				</THEN>
			</IF>
			<IF>
				<CONDITION>Len(Transaction.Comment)</CONDITION>
				<THEN>
					<ROW>"Comment:|" Transaction.Comment </ROW>
				</THEN>
			</IF>
		</TABLE>
		<!--
   ===========================
   Store Logo
   ===========================
-->
		<IF>
			<CONDITION> ShowLogo </CONDITION>
			<THEN>
				<PICTURE>
					<FILENAME>  LogoFilename        </FILENAME>
					<WIDTH>     PageWidth * 0.15    </WIDTH>
					<LEFT>      MarginLeft          </LEFT>
					<TOP>          MarginTop + 0.1         </TOP>
				</PICTURE>
			</THEN>
		</IF>
	</SUB>
	<!--
   ===========================
   Draw Footer
   ===========================
-->
	<SUB name="DrawFooter">
		<MARGIN>
			<BOTTOM>    MarginBottom   </BOTTOM>
		</MARGIN>
		<TABLE>
			<TOP> PaperHeight - MarginBottom - FooterHeight </TOP>
			<FONT> "Small" </FONT>
			<BORDER> tbNone </BORDER>
			<COLUMNHEADER>
				<ALIGNMENT> "&lt;~" </ALIGNMENT>
				<WIDTH> PageWidth </WIDTH>
				<TEXT></TEXT>
			</COLUMNHEADER>
			<ROW> "Continued on next page..." </ROW>
		</TABLE>
	</SUB>
	<!--
   ===========================
   Draw Last Footer
   ===========================
-->
	<SUB name="DrawLastFooter">
		<MARGIN>
			<BOTTOM>    MarginBottom   </BOTTOM>
		</MARGIN>
		<TABLE>
			<TOP> PaperHeight - MarginBottom - FooterHeight </TOP>
			<FONT> "Small" </FONT>
			<BORDER> tbNone </BORDER>
			<HEADERSHADE> LineColor </HEADERSHADE>
			<IF>
				<CONDITION> (Transaction.Type = TransactionWorkOrder) | (Transaction.Type = TransactionLayaway) </CONDITION>
				<THEN>
					<IF>
						<CONDITION> ShowTotalQuantity  </CONDITION>
						<THEN>
							<COLUMNHEADER>
								<ALIGNMENT>    "^~"     </ALIGNMENT>
								<WIDTH> PageWidth </WIDTH>
								<TEXT>         "!!!!! Total " Transaction.TotalQuantity " QTY, " Transaction.TotalQuantityPurchased " PKD, " Transaction.TotalQuantityOnOrder " ORD ITEMS !!!!!" </TEXT>
								<!--				<TEXT> "DDDDDDD " </TEXT>
-->
							</COLUMNHEADER>
						</THEN>
						<ELSE>
							<COLUMNHEADER>
								<ALIGNMENT>    "^~"     </ALIGNMENT>
								<WIDTH> PageWidth </WIDTH>
								<!--				<TEXT> "DDDDDDD " </TEXT>
-->
							</COLUMNHEADER>
						</ELSE>
					</IF>
				</THEN>
				<ELSE>
					<IF>
						<CONDITION> ShowTotalQuantity  </CONDITION>
						<THEN>
							<COLUMNHEADER>
								<ALIGNMENT>    "^~"     </ALIGNMENT>
								<WIDTH> PageWidth </WIDTH>
								<TEXT>         "!!!!! Total " Transaction.TotalQuantity " QTY Items !!!!!" </TEXT>
								<!--				<TEXT> "DDDDDDD " </TEXT>
-->
							</COLUMNHEADER>
						</THEN>
						<ELSE>
							<COLUMNHEADER>
								<ALIGNMENT>    "^~"     </ALIGNMENT>
								<WIDTH> PageWidth </WIDTH>
								<!--				<TEXT> "DDDDDDD " </TEXT>
-->
							</COLUMNHEADER>
						</ELSE>
					</IF>
				</ELSE>
			</IF>
		</TABLE>
		<IF>
			<CONDITION>Transaction.Type = transactionSales | Transaction.Type = transactionWorkOrder | Transaction.Type = transactionQuote | Transaction.Type = transactionBackOrder | Transaction.Type = transactionLayaway</CONDITION>
			<THEN>
				<TABLE>
					<FONT> "Small" </FONT>
					<BORDER> tbNone </BORDER>
					<COLUMNHEADER>
						<ALIGNMENT> "&gt;~" </ALIGNMENT>
						<WIDTH> PageWidth * 0.85 </WIDTH>
						<TEXT> "Sub Total" </TEXT>
					</COLUMNHEADER>
					<COLUMNHEADER>
						<ALIGNMENT> "&gt;~" </ALIGNMENT>
						<WIDTH> PageWidth * 0.15 </WIDTH>
						<TEXT> Transaction.SubTotal </TEXT>
					</COLUMNHEADER>
					<IF>
						<CONDITION> ShowSalesTax </CONDITION>
						<THEN>
							<IF>
								<CONDITION> ShowTaxDetails </CONDITION>
								<THEN>
									<FOR each="SalesTaxes">
										<IF>
											<CONDITION> Transaction.SalesTaxes.ShowOnReceipt &amp; Transaction.SalesTaxes.IsTransactionMember </CONDITION>
											<THEN>
												<ROW> Transaction.SalesTaxes.Description "|" Transaction.SalesTaxes.Total </ROW>
											</THEN>
										</IF>
									</FOR>
								</THEN>
								<ELSE>
									<ROW> "Sales Tax|" Transaction.SalesTax </ROW>
								</ELSE>
							</IF>
						</THEN>
					</IF>
					<IF>
						<CONDITION> Len(Shipping.Carrier) </CONDITION>
						<THEN>
							<ROW> Shipping.Carrier " " Shipping.Service "|" Shipping.Charge </ROW>
							<IF>
								<CONDITION> Len(Shipping.Notes) </CONDITION>
								<THEN>
									<ROW> Shipping.Notes "|" </ROW>
								</THEN>
							</IF>
							<IF>
								<CONDITION> Len(Shipping.TrackingNumber) </CONDITION>
								<THEN>
									<ROW> Shipping.TrackingNumber "|" </ROW>
								</THEN>
							</IF>
						</THEN>
					</IF>
					<IF>
						<CONDITION> Transaction.DebitSurcharge </CONDITION>
						<THEN>
							<ROW> "Debit Surcharges|" Transaction.DebitSurcharge </ROW>
						</THEN>
					</IF>
					<IF>
						<CONDITION> Transaction.CashBackSurcharge </CONDITION>
						<THEN>
							<ROW> "Cash Back Surcharges|" Transaction.CashBackSurcharge </ROW>
						</THEN>
					</IF>
					<ROW> "Total|" Transaction.Total </ROW>
					<ROW> " " </ROW>
					<IF>
						<CONDITION> (Transaction.TotalDue &lt;&gt; Transaction.Total) &amp; (Transaction.Type &lt;&gt; transactionQuote) </CONDITION>
						<THEN>
							<ROW> "Deposit Payment|" Transaction.Deposit </ROW>
							<ROW> "Total Purchased|" Transaction.TotalPurchased </ROW>
							<ROW> "Total Due|" Transaction.TotalDue </ROW>
							<ROW></ROW>
						</THEN>
					</IF>
					<FOR each="tender">
						<IF>
							<CONDITION> (Tender.AmountIn &lt;&gt; 0) | (Tender.AmountInRounding &lt;&gt; 0) </CONDITION>
							<THEN>
								<IF>
									<CONDITION> Tender.Descriptor.TenderType = tenderAccount </CONDITION>
									<THEN>
										<ROW> Tender.Descriptor.Description "|" Tender.AmountIn </ROW>
									</THEN>
									<ELSE>
										<ROW> Tender.Descriptor.Description " Tendered|" Tender.AmountIn </ROW>
									</ELSE>
								</IF>
								<IF>
									<CONDITION> Tender.Descriptor.TenderType = tenderCreditCard | Tender.Descriptor.TenderType = tenderDebitCard </CONDITION>
									<THEN>
										<IF>
											<CONDITION> MaskCreditCard </CONDITION>
											<THEN>
												<ROW> "Card: " Tender.AccountNumberMasked "|" </ROW>
											</THEN>
											<ELSE>
												<ROW> "Card: " Tender.AccountNumber "|" </ROW>
											</ELSE>
										</IF>
										<ROW> "Exp: " Tender.Expiration "|" </ROW>
										<ROW> "Auth: " Tender.Approvalcode "|" </ROW>
									</THEN>
								</IF>
								<IF>
									<CONDITION> (Tender.Descriptor.TenderType = tenderAccount) &amp; ShowAccountBalance </CONDITION>
									<THEN>
										<SET name="NewAccountBalance" type="vbcurrency">  Customer.AccountBalance + Tender.AmountIn - Tender.AmountOut </SET>
										<ROW> "Previous Balance|" Customer.AccountBalance </ROW>
										<ROW> "New Balance|" NewAccountBalance </ROW>
										<ROW></ROW>
									</THEN>
								</IF>
								<IF>
									<CONDITION> Tender.Descriptor.TenderType = tenderVoucher </CONDITION>
									<THEN>
										<ROW> "Number:" Tender.VoucherNumber "|" </ROW>
										<ROW> "Previous Balance|" Tender.VoucherPreviousBalance </ROW>
										<ROW> "New Balance|" Tender.VoucherNewBalance </ROW>
										<ROW></ROW>
									</THEN>
								</IF>
								<IF>
									<CONDITION> Tender.AmountInRounding &lt;&gt; 0 </CONDITION>
									<THEN>
										<ROW> "Roundoff " Tender.Descriptor.Description "|" Tender.AmountInRounding </ROW>
									</THEN>
								</IF>
							</THEN>
						</IF>
					</FOR>
					<IF>
						<CONDITION> Transaction.TotalTenderOut </CONDITION>
						<THEN>
							<FOR each="tender">
								<IF>
									<CONDITION> Tender.AmountOut &lt;&gt; 0 | Tender.AmountOutRounding &lt;&gt; 0 </CONDITION>
									<THEN>
										<ROW> "Change " Tender.Descriptor.Description "|" Tender.AmountOut </ROW>
										<IF>
											<CONDITION> Tender.Descriptor.TenderType = tenderCreditCard  | Tender.Descriptor.TenderType = tenderDebitCard </CONDITION>
											<THEN>
												<IF>
													<CONDITION> MaskCreditCard </CONDITION>
													<THEN>
														<ROW> "Card: " Tender.AccountNumberMasked "|" </ROW>
													</THEN>
													<ELSE>
														<ROW> "Card: " Tender.AccountNumber "|" </ROW>
													</ELSE>
												</IF>
												<ROW> "Auth: " Tender.ApprovalCode "|" </ROW>
											</THEN>
										</IF>
										<IF>
											<CONDITION> (Tender.Descriptor.TenderType = tenderAccount) &amp; ShowAccountBalance </CONDITION>
											<THEN>
												<SET name="NewAccountBalance" type="vbcurrency">  Customer.AccountBalance + Tender.AmountIn - Tender.AmountOut </SET>
												<ROW> "Previous Balance|" Customer.AccountBalance </ROW>
												<ROW> "New Balance|" NewAccountBalance </ROW>
												<ROW></ROW>
											</THEN>
										</IF>
										<IF>
											<CONDITION> Tender.AmountOutRounding &lt;&gt; 0 </CONDITION>
											<THEN>
												<ROW> "Roundoff " Tender.Descriptor.Description "|" Tender.AmountOutRounding </ROW>
											</THEN>
										</IF>
									</THEN>
								</IF>
							</FOR>
						</THEN>
						<ELSE>
							<ROW> "Change Due|" Transaction.TotalTenderOut </ROW>
						</ELSE>
					</IF>
					<IF>
						<CONDITION> (Transaction.TotalDue &lt;&gt; Transaction.Total) &amp; (Transaction.Type &lt;&gt; transactionQuote) </CONDITION>
						<THEN>
							<ROW></ROW>
							<ROW> "Remaining Deposit|" Transaction.DepositTotal </ROW>
							<ROW> "New Balance|" Transaction.OrderBalanceNew </ROW>
						</THEN>
					</IF>
				</TABLE>
			</THEN>
		</IF>
		<IF>
			<CONDITION> Transaction.Type = transactionAccountPayment </CONDITION>
			<THEN>
				<TABLE>
					<FONT> "Small" </FONT>
					<BORDER> tbNone </BORDER>
					<COLUMNHEADER>
						<ALIGNMENT> "&gt;~" </ALIGNMENT>
						<WIDTH> PageWidth * 0.85 </WIDTH>
						<TEXT> "Total Payments" </TEXT>
					</COLUMNHEADER>
					<COLUMNHEADER>
						<ALIGNMENT> "&gt;~" </ALIGNMENT>
						<WIDTH> PageWidth * 0.15 </WIDTH>
						<TEXT> Customer.AccountReceivables.TotalPayments </TEXT>
					</COLUMNHEADER>
					<IF>
						<CONDITION> Customer.AccountReceivables.AppliedCredits &lt;&gt; 0 </CONDITION>
						<THEN>
							<ROW> "Applied Credit|" Customer.AccountReceivables.AppliedCredits </ROW>
						</THEN>
					</IF>
					<FOR each="tender">
						<IF>
							<CONDITION> Tender.AmountIn &lt;&gt; 0 </CONDITION>
							<THEN>
								<ROW> "Paid " Tender.Descriptor.Description "|" Tender.AmountIn </ROW>
								<IF>
									<CONDITION> Tender.Descriptor.TenderType = tenderCreditCard  | Tender.Descriptor.TenderType = tenderDebitCard </CONDITION>
									<THEN>
										<IF>
											<CONDITION> MaskCreditCard </CONDITION>
											<THEN>
												<ROW> "Card: " Tender.AccountNumberMasked "|" </ROW>
											</THEN>
											<ELSE>
												<ROW> "Card: " Tender.AccountNumber "|" </ROW>
											</ELSE>
										</IF>
										<ROW> "Exp: " Tender.Expiration "|" </ROW>
										<ROW> "Auth: " Tender.ApprovalCode "|" </ROW>
									</THEN>
								</IF>
								<IF>
									<CONDITION> Tender.AmountInRounding &lt;&gt; 0 </CONDITION>
									<THEN>
										<ROW> "RoundOff " Tender.Descriptor.Description "|" Tender.AmountInRounding </ROW>
									</THEN>
								</IF>
							</THEN>
						</IF>
					</FOR>
					<FOR each="tender">
						<IF>
							<CONDITION> Tender.AmountOut &lt;&gt; 0 </CONDITION>
							<THEN>
								<ROW> "Paid " Tender.Descriptor.Description "|" Tender.AmountOut </ROW>
								<IF>
									<CONDITION> Tender.Descriptor.TenderType = tenderCreditCard  | Tender.Descriptor.TenderType = tenderDebitCard </CONDITION>
									<THEN>
										<IF>
											<CONDITION> MaskCreditCard </CONDITION>
											<THEN>
												<ROW> "Card: " Tender.AccountNumberMasked "|" </ROW>
											</THEN>
											<ELSE>
												<ROW> "Card: " Tender.AccountNumber "|" </ROW>
											</ELSE>
										</IF>
										<ROW> "Auth: " Tender.ApprovalCode "|" </ROW>
									</THEN>
								</IF>
								<IF>
									<CONDITION> Tender.AmountOutRounding &lt;&gt; 0 </CONDITION>
									<THEN>
										<ROW> "RoundOff " Tender.Descriptor.Description "|" Tender.AmountOutRounding </ROW>
									</THEN>
								</IF>
							</THEN>
						</IF>
					</FOR>
					<ROW></ROW>
					<ROW> "Previous Balance|" Customer.PreviousAccountBalance </ROW>
					<ROW> "Payments|" Customer.AccountReceivables.TotalPayments </ROW>
					<ROW> "New Balance|" Customer.AccountBalance </ROW>
					<ROW></ROW>
				</TABLE>
			</THEN>
		</IF>
		<IF>
			<CONDITION> ShowComments </CONDITION>
			<THEN>
				<TABLE>
					<BORDER> tbNone </BORDER>
					<TOP>PaperHeight - MarginBottom - FooterHeight + 0.2</TOP>
					<COLUMNHEADER>
						<ALIGNMENT>"&lt;"</ALIGNMENT>
						<WIDTH>PageWidth * 0.50</WIDTH>
						<TEXT newline="true"></TEXT>
						<TEXT newline="true">CommentLine1 </TEXT>
						<TEXT newline="true">CommentLine2</TEXT>
						<TEXT newline="true">CommentLine3</TEXT>
						<TEXT newline="true">CommentLine4</TEXT>
						<TEXT newline="true">CommentLine5</TEXT>
						<TEXT newline="true"></TEXT>
					</COLUMNHEADER>
				</TABLE>
			</THEN>
		</IF>
		<!--
   ===========================
   Barcode
   ===========================
		<IF>
			<CONDITION> ShowBarcode &amp; (Transaction.ReceiptTransactionNumber &lt;&gt; 0) </CONDITION>
			<THEN>
				<BARCODE>
					<TOP>          PaperHeight - MarginBottom - 0.5     </TOP>
					<STYLE>        msS3of9              </STYLE>
					<UPCNOTCHES>   msUPCNBelow          </UPCNOTCHES>
					<LEFT>         MarginLeft           </LEFT>
					<WIDTH>        PageWidth * .40      </WIDTH>
					<HEIGHT>       0.2                  </HEIGHT>
					<PRINTCAPTION> True                 </PRINTCAPTION>
					<BARWIDTH>     0                    </BARWIDTH>
					<TEXT>   Transaction.ReceiptTransactionNumber </TEXT>
				</BARCODE>
			</THEN>
		</IF>
-->
		<IF>
			<CONDITION> ShowPreBalance </CONDITION>
			<THEN>
				<TABLE>
					<BORDER> tbNone </BORDER>
					<TOP>HeaderHeight + MarginTop - 0.4</TOP>
					<COLUMNHEADER>
						<ALIGNMENT> "&gt;" </ALIGNMENT>
						<WIDTH> PageWidth * 0.85 </WIDTH>
						<TEXT> "" </TEXT>
					</COLUMNHEADER>
					<COLUMNHEADER>
						<ALIGNMENT> "&gt;" </ALIGNMENT>
						<WIDTH> PageWidth * 0.15 </WIDTH>
						<TEXT> "" </TEXT>
					</COLUMNHEADER>
					<IF>
						<CONDITION>Len(Customer.AccountBalance)</CONDITION>
						<THEN>
							<ROW> "Total A/R Balance:|" Customer.AccountBalance </ROW>
						</THEN>
					</IF>
				</TABLE>
			</THEN>
		</IF>
		<IF>
			<CONDITION> ShowBarcode &amp; (Transaction.ReceiptTransactionNumber &lt;&gt; 0) </CONDITION>
			<THEN>
				<BARCODE>
					<TOP>          PaperHeight - MarginBottom  - 0.1    </TOP>
					<STYLE>        msS3of9              </STYLE>
					<UPCNOTCHES>   msUPCNBelow          </UPCNOTCHES>
					<LEFT>         MarginLeft           </LEFT>
					<WIDTH>        PageWidth * .35      </WIDTH>
					<HEIGHT>       0.2                  </HEIGHT>
					<PRINTCAPTION> True                 </PRINTCAPTION>
					<BARWIDTH>     0                    </BARWIDTH>
					<TEXT>   Transaction.ReceiptTransactionNumber </TEXT>
				</BARCODE>
			</THEN>
		</IF>
		<IF>
			<CONDITION> ShowBComments </CONDITION>
			<THEN>
				<TABLE>
					<BORDER> tbNone </BORDER>
					<TOP>PaperHeight - MarginBottom - 0.7</TOP>
					<COLUMNHEADER>
						<ALIGNMENT>"&lt;"</ALIGNMENT>
						<WIDTH>PageWidth * 0.50</WIDTH>
						<TEXT newline="true">BCommentLine1 </TEXT>
						<TEXT newline="true">BCommentLine2</TEXT>
						<TEXT newline="true">BCommentLine3</TEXT>
					</COLUMNHEADER>
				</TABLE>
			</THEN>
		</IF>
	</SUB>
	<!--
   ===========================
   Draw Duplicate
   ===========================
-->
	<SUB name="DrawDuplicate">
		<MARGIN>
			<BOTTOM>    MarginBottom   </BOTTOM>
			<TOP>       MarginTop   </TOP>
		</MARGIN>
		<TABLE>
			<TOP> PaperHeight / 2 </TOP>
			<FONT> "Huge" </FONT>
			<BORDER> tbNone </BORDER>
			<COLUMNHEADER>
				<ALIGNMENT> "^~" </ALIGNMENT>
				<WIDTH> PageWidth </WIDTH>
				<TEXT>"DUPLICATE RECEIPT"</TEXT>
			</COLUMNHEADER>
		</TABLE>
	</SUB>
	<SUB name="OverlayFirstPage">
		<CALL> "DrawHeader" </CALL>
		<CALL> "DrawFooter" </CALL>
	</SUB>
	<SUB name="OverlayMiddlePage">
		<CALL> "DrawHeader" </CALL>
		<CALL> "DrawFooter" </CALL>
	</SUB>
	<SUB name="OverlayLastPage">
		<CALL> "DrawHeader" </CALL>
		<CALL> "DrawLastFooter" </CALL>
	</SUB>
	<SUB name="OverlayOnlyPage">
		<CALL> "DrawHeader" </CALL>
		<CALL> "DrawLastFooter" </CALL>
	</SUB>
	<SUB name="Duplicate">
		<IF>
			<CONDITION> ShowDuplicate </CONDITION>
			<THEN>
				<CALL> "DrawDuplicate" </CALL>
			</THEN>
		</IF>
	</SUB>
	<!--
   ===========================
   Document
   ===========================
-->
	<DOCUMENT>
		<!--
   ===========================
   Drop & Payout
   ===========================
-->
		<IF>
			<CONDITION> Transaction.Type = transactionDrop | Transaction.Type = transactionPayOut </CONDITION>
			<THEN>
				<TABLE>
					<TOP> HeaderHeight + MarginTop </TOP>
					<BORDER> tbNone </BORDER>
					<HEADERSHADE> LineColor </HEADERSHADE>
					<COLUMNHEADER>
						<ALIGNMENT> "&gt;" </ALIGNMENT>
						<WIDTH> PageWidth * 0.50 </WIDTH>
					</COLUMNHEADER>
					<COLUMNHEADER>
						<ALIGNMENT> "&lt;" </ALIGNMENT>
						<WIDTH> PageWidth * 0.50 </WIDTH>
					</COLUMNHEADER>
					<ROW></ROW>
					<IF>
						<CONDITION> Transaction.Type = transactionPayout </CONDITION>
						<THEN>
							<ROW> "Pay To:|" Transaction.PayOutRecipient </ROW>
						</THEN>
					</IF>
					<ROW> "Comment:|" Transaction.Comment </ROW>
					<ROW></ROW>
					<FOR each="tender">
						<IF>
							<CONDITION> Tender.AmountOut &lt;&gt; 0 </CONDITION>
							<THEN>
								<ROW> "Amount Out (" Tender.Descriptor.Description "):|" Tender.AmountOut </ROW>
							</THEN>
						</IF>
					</FOR>
					<ROW></ROW>
					<FOR each="tender">
						<IF>
							<CONDITION> Tender.AmountIn &lt;&gt; 0 </CONDITION>
							<THEN>
								<ROW> "Amount In (" Tender.Descriptor.Description "):|" Tender.AmountIn </ROW>
							</THEN>
						</IF>
					</FOR>
				</TABLE>
			</THEN>
		</IF>
		<!--
      ============================
      Account Payment - Receivable date
      ============================
   -->
		<IF>
			<CONDITION> (Transaction.Type = transactionAccountPayment) &amp; (Customer.AccountDateDueType = accountdueAccountReceivableDatePlusGracePeriod) </CONDITION>
			<THEN>
				<TABLE>
					<TOP> HeaderHeight + MarginTop </TOP>
					<FONT> "Small" </FONT>
					<BORDER> tbNone </BORDER>
					<HEADERSHADE> LineColor </HEADERSHADE>
					<COLUMNHEADER>
						<ALIGNMENT> "&lt;" </ALIGNMENT>
						<WIDTH> PageWidth * 0.25 </WIDTH>
						<TEXT> "Reference" </TEXT>
					</COLUMNHEADER>
					<COLUMNHEADER>
						<ALIGNMENT> "&gt;" </ALIGNMENT>
						<WIDTH> PageWidth * 0.15 </WIDTH>
						<TEXT> "Invoice Date:" </TEXT>
					</COLUMNHEADER>
					<COLUMNHEADER>
						<ALIGNMENT> "&gt;" </ALIGNMENT>
						<WIDTH> PageWidth * 0.15 </WIDTH>
						<TEXT> "Due Date:" </TEXT>
					</COLUMNHEADER>
					<COLUMNHEADER>
						<ALIGNMENT> "&gt;" </ALIGNMENT>
						<WIDTH> PageWidth * 0.15 </WIDTH>
						<TEXT> "Invoice Amount:" </TEXT>
					</COLUMNHEADER>
					<COLUMNHEADER>
						<ALIGNMENT> "&gt;" </ALIGNMENT>
						<WIDTH> PageWidth * 0.15 </WIDTH>
						<TEXT> "Balance Due:" </TEXT>
					</COLUMNHEADER>
					<COLUMNHEADER>
						<ALIGNMENT> "&gt;" </ALIGNMENT>
						<WIDTH> PageWidth * 0.15 </WIDTH>
						<TEXT> "Payment:" </TEXT>
					</COLUMNHEADER>
					<FOR each="AccountReceivable">
						<IF>
							<CONDITION> (Customer.AccountReceivable.Payment &lt;&gt; 0) | (Customer.AccountReceivable.Balance &lt;&gt; 0) </CONDITION>
							<THEN>
								<ROW> Customer.AccountReceivable.Reference "|" Customer.AccountReceivable.OriginalDate "|" Customer.AccountReceivable.DueDate "|" Customer.AccountReceivable.OriginalAmount "|" Customer.AccountReceivable.Balance "|" Customer.AccountReceivable.Payment </ROW>
							</THEN>
						</IF>
					</FOR>
				</TABLE>
			</THEN>
		</IF>
		<!--
      ============================
      Account Payment - Revolving
      ============================
   -->
		<IF>
			<CONDITION> (Transaction.Type = transactionAccountPayment) &amp; (Customer.AccountDateDueType = accountdueCloseOfBillingCyclePlusGracePeriod) </CONDITION>
			<THEN>
				<TABLE>
					<TOP> HeaderHeight + MarginTop </TOP>
					<FONT> "Small" </FONT>
					<BORDER> tbNone </BORDER>
					<HEADERSHADE> LineColor </HEADERSHADE>
					<COLUMNHEADER>
						<ALIGNMENT> "&lt;" </ALIGNMENT>
						<WIDTH> PageWidth  </WIDTH>
						<TEXT> "" </TEXT>
					</COLUMNHEADER>
					<ROW> "Payment on Account..." </ROW>
				</TABLE>
			</THEN>
		</IF>
		<!--
   ===========================
   Transaction Details
   ===========================
-->
		<IF>
			<CONDITION> Transaction.Type = transactionSales | Transaction.Type = transactionWorkOrder | Transaction.Type = transactionQuote | Transaction.Type = transactionBackOrder | Transaction.Type = transactionLayaway | Transaction.Type = transactionAbortedTransaction </CONDITION>
			<THEN>
				<TABLE>
					<TOP> HeaderHeight + MarginTop </TOP>
					<FONT> "Small" </FONT>
					<BORDER> tbAll </BORDER>
					<HEADERSHADE> LineColor </HEADERSHADE>
					<COLUMNHEADER>
						<ALIGNMENT> "&gt;" </ALIGNMENT>
						<WIDTH> PageWidth * 0.06 </WIDTH>
						<TEXT> "LN." </TEXT>
					</COLUMNHEADER>
					<COLUMNHEADER>
						<ALIGNMENT> "&lt;" </ALIGNMENT>
						<WIDTH> PageWidth * 0.40 </WIDTH>
						<TEXT> "Description" </TEXT>
					</COLUMNHEADER>
					<COLUMNHEADER>
						<ALIGNMENT> "&gt;" </ALIGNMENT>
						<WIDTH> PageWidth * 0.12 </WIDTH>
						<TEXT> "U-Price" </TEXT>
					</COLUMNHEADER>
					<COLUMNHEADER>
						<ALIGNMENT> "&lt;" </ALIGNMENT>
						<WIDTH> PageWidth * 0.12 </WIDTH>
						<TEXT> "Pack" </TEXT>
					</COLUMNHEADER>
					<COLUMNHEADER>
						<ALIGNMENT> "&gt;" </ALIGNMENT>
						<WIDTH> PageWidth * 0.08 </WIDTH>
						<TEXT> "Qty" </TEXT>
					</COLUMNHEADER>
					<COLUMNHEADER>
						<ALIGNMENT> "&gt;" </ALIGNMENT>
						<WIDTH> PageWidth * 0.10 </WIDTH>
						<TEXT> "Price" </TEXT>
					</COLUMNHEADER>
					<COLUMNHEADER>
						<ALIGNMENT> "&gt;" </ALIGNMENT>
						<WIDTH> PageWidth * 0.12 </WIDTH>
						<TEXT> "Extended" </TEXT>
					</COLUMNHEADER>
					<FOR each="Entry">
						<SET name="LineNo" type="vbLong">  NewLineNo + 1 </SET>
						<IF>
							<CONDITION> ShowLineDiscounts &amp; (Entry.ExtendedDiscountPurchased &lt;&gt; 0)</CONDITION>
							<THEN>
								<SET name="UnitPrice" type="vbcurrency"> Entry.Price / Entry.Item.Weight </SET>
								<ROW> LineNo "|" Entry.Description "|" UnitPrice "|"Entry.Item.Weight "" Entry.Item.UnitOfMeasure "|"  Entry.Quantity "|" Entry.FullPrice "|" Entry.ExtendedFullPrice </ROW>
								<SET name="TotalExciseTax" type="vbcurrency"> TotalExciseTax + (Entry.Quantity * Entry.Item.PriceC) </SET>
								<IF>
									<CONDITION> Entry.DiscountNegative &lt;&gt; 0 </CONDITION>
									<THEN>
										<ROW>  "|Discount||||" Entry.DiscountNegative "|" Entry.ExtendedDiscountNegative </ROW>
									</THEN>
								</IF>
							</THEN>
							<ELSE>
								<SET name="UnitPrice" type="vbcurrency"> Entry.Price / Entry.Item.Weight </SET>
								<ROW> LineNo "|" Entry.Description "|" UnitPrice "|"Entry.Item.Weight "" Entry.Item.UnitOfMeasure "|"  Entry.Quantity "|" Entry.Price "|" Entry.ExtendedPrice </ROW>
								<SET name="TotalExciseTax" type="vbcurrency"> TotalExciseTax + (Entry.Quantity * Entry.Item.PriceC) </SET>
							</ELSE>
						</IF>
						<IF>
							<CONDITION> ((Entry.QuantityOnOrder &lt;&gt; 0) | (Entry.QuantityRTD &lt;&gt; 0)) &amp; (Transaction.Type &lt;&gt; transactionQuote) </CONDITION>
							<THEN>
								<ROW> "|Quantity RTD:|||" Entry.QuantityRTD "   ||" </ROW>
								<ROW> "|Quantity On Order:|||" Entry.QuantityOnOrder "   ||" </ROW>
								<ROW> "|Quantity Picked Up:|||" Entry.QuantityPurchased "   ||" </ROW>
								<ROW>
								</ROW>
							</THEN>
						</IF>
						<SET name="NewLineNo" type="vbLong">  LineNo </SET>
					</FOR>
					<IF><CONDITION>TotalExciseTax &lt;&gt; 0 </CONDITION>
						<THEN>
							<ROW> "" </ROW>
							<ROW> "|" ExciseTaxBegin "  " TotalExciseTax "|||||" </ROW>
							<ROW> "|" ExciseTaxEnd "|||||" </ROW>
						</THEN>
					</IF>
					<IF>
						<CONDITION> ShowTotalSaving  </CONDITION>
						<THEN>
							<IF>
								<CONDITION> (Transaction.Discount  &lt;&gt; 0) </CONDITION>
								<THEN>
									<ROW>  "||||||" </ROW>
									<ROW>  "|Total Discount " Transaction.Discount "|||||" </ROW>
								</THEN>
							</IF>
						</THEN>
					</IF>
				</TABLE>
				<!--
   ===========================
   Canceled Transaction
   ===========================
-->
				<IF>
					<CONDITION> Transaction.Type = transactionAbortedTransaction </CONDITION>
					<THEN>
						<TABLE>
							<BORDER> tbNone </BORDER>
							<COLUMNHEADER>
								<ALIGNMENT> "&lt;~" </ALIGNMENT>
								<WIDTH> PageWidth </WIDTH>
							</COLUMNHEADER>
							<ROW> "" </ROW>
							<ROW> "Transaction cancelled..." </ROW>
							<ROW> "" </ROW>
							<ROW> "" </ROW>
						</TABLE>
					</THEN>
				</IF>
			</THEN>
		</IF>
	</DOCUMENT>
</XML>

```

## Usage

This XML template is processed by Microsoft Retail Management System to generate formatted receipts for printing on standard 8.5" x 11" paper.

**Template Size**: 41,195 characters
