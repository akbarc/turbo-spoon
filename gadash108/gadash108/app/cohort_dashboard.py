"""
Sales Cohort Analysis Dashboard Routes
"""

from flask import Flask, render_template, jsonify, request
import json
import pandas as pd
from datetime import datetime, timedelta
import logging
from modules.ar.sales_cohort_analyzer import SalesCohortAnalyzer

logger = logging.getLogger(__name__)

def register_cohort_routes(app):
    """Register cohort analysis routes with the Flask app"""
    
    analyzer = SalesCohortAnalyzer()
    
    @app.route('/cohort-dashboard')
    def cohort_dashboard():
        """Main cohort analysis dashboard"""
        return render_template('cohort_dashboard.html')
    
    @app.route('/api/cohort/analysis')
    def get_cohort_analysis():
        """Get comprehensive cohort analysis"""
        try:
            # Get filter parameters
            weeks = request.args.get('weeks', 12, type=int)
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            # Create analyzer with appropriate lookback period
            if start_date and end_date:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                weeks = int((end - start).days / 7)
                filtered_analyzer = SalesCohortAnalyzer(lookback_weeks=weeks, start_date=start, end_date=end)
            else:
                filtered_analyzer = SalesCohortAnalyzer(lookback_weeks=weeks)
            analysis = filtered_analyzer.analyze_collection_patterns()
            
            # Convert CohortMetrics objects to dicts
            if 'cohort_metrics' in analysis:
                metrics_dict = {}
                for key, metric in analysis['cohort_metrics'].items():
                    metrics_dict[key] = {
                        'cohort_week': metric.cohort_week,
                        'sales_amount': metric.sales_amount,
                        'collections_by_week': metric.collections_by_week,
                        'cumulative_collection_rate': metric.cumulative_collection_rate,
                        'dso': metric.dso,
                        'total_collected': metric.total_collected,
                        'total_outstanding': metric.total_outstanding,
                        'collection_velocity': metric.collection_velocity
                    }
                analysis['cohort_metrics'] = metrics_dict
            
            return jsonify({
                'success': True,
                'data': analysis
            })
        except Exception as e:
            logger.error(f"Error in cohort analysis: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/cohort/waterfall')
    def get_waterfall_data():
        """Get waterfall chart data"""
        try:
            # Get filter parameters
            weeks = request.args.get('weeks', 12, type=int)
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            num_cohorts = request.args.get('cohorts', weeks, type=int)
            
            # Create analyzer with appropriate lookback period
            if start_date and end_date:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                weeks = int((end - start).days / 7)
                filtered_analyzer = SalesCohortAnalyzer(lookback_weeks=weeks, start_date=start, end_date=end)
            else:
                filtered_analyzer = SalesCohortAnalyzer(lookback_weeks=weeks)
            data = filtered_analyzer.get_waterfall_data(num_cohorts)
            
            return jsonify({
                'success': True,
                'data': data
            })
        except Exception as e:
            logger.error(f"Error getting waterfall data: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/cohort/velocity')
    def get_velocity_curves():
        """Get collection velocity curves"""
        try:
            # Get filter parameters
            weeks = request.args.get('weeks', 12, type=int)
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            # Create analyzer with appropriate lookback period
            if start_date and end_date:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                weeks = int((end - start).days / 7)
                filtered_analyzer = SalesCohortAnalyzer(lookback_weeks=weeks, start_date=start, end_date=end)
            else:
                filtered_analyzer = SalesCohortAnalyzer(lookback_weeks=weeks)
            curves = filtered_analyzer.get_velocity_curves()
            
            # Convert to format suitable for charting
            chart_data = []
            for cohort, curve in curves.items():
                chart_data.append({
                    'cohort': cohort,
                    'data': [{'week': w, 'rate': r} for w, r in curve]
                })
            
            return jsonify({
                'success': True,
                'data': chart_data
            })
        except Exception as e:
            logger.error(f"Error getting velocity curves: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/cohort/aging')
    def get_aging_analysis():
        """Get aging analysis"""
        try:
            # Get filter parameters
            weeks = request.args.get('weeks', 12, type=int)
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            # Create analyzer with appropriate lookback period
            if start_date and end_date:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                weeks = int((end - start).days / 7)
                filtered_analyzer = SalesCohortAnalyzer(lookback_weeks=weeks, start_date=start, end_date=end)
            else:
                filtered_analyzer = SalesCohortAnalyzer(lookback_weeks=weeks)
            aging_df = filtered_analyzer.get_aging_analysis()
            
            if not aging_df.empty:
                data = aging_df.to_dict('records')
            else:
                data = []
            
            return jsonify({
                'success': True,
                'data': data
            })
        except Exception as e:
            logger.error(f"Error getting aging analysis: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/cohort/dso')
    def get_cohort_dso():
        """Get DSO by cohort"""
        try:
            # Get filter parameters
            weeks = request.args.get('weeks', 12, type=int)
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            # Create analyzer with appropriate lookback period
            if start_date and end_date:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                weeks = int((end - start).days / 7)
                filtered_analyzer = SalesCohortAnalyzer(lookback_weeks=weeks, start_date=start, end_date=end)
            else:
                filtered_analyzer = SalesCohortAnalyzer(lookback_weeks=weeks)
            dso_df = filtered_analyzer.calculate_cohort_dso()
            
            if not dso_df.empty:
                # Convert dates to strings for JSON
                dso_df['WeekStart'] = dso_df['WeekStart'].astype(str)
                data = dso_df.to_dict('records')
            else:
                data = []
            
            return jsonify({
                'success': True,
                'data': data
            })
        except Exception as e:
            logger.error(f"Error calculating DSO: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/cohort/predictions')
    def get_predictions():
        """Get cash flow predictions based on cohort patterns"""
        try:
            # Get filter parameters
            weeks = request.args.get('weeks', 12, type=int)
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            # Create analyzer with appropriate lookback period
            if start_date and end_date:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                weeks = int((end - start).days / 7)
                filtered_analyzer = SalesCohortAnalyzer(lookback_weeks=weeks, start_date=start, end_date=end)
            else:
                filtered_analyzer = SalesCohortAnalyzer(lookback_weeks=weeks)
            analysis = filtered_analyzer.analyze_collection_patterns()
            predictions = analysis.get('predictions', {})
            
            # Format for chart display
            chart_data = []
            for week_key, pred in predictions.items():
                chart_data.append({
                    'week': week_key,
                    'expected': pred['expected_collections'],
                    'confidence': pred['confidence']
                })
            
            return jsonify({
                'success': True,
                'data': chart_data,
                'summary': analysis.get('summary', {})
            })
        except Exception as e:
            logger.error(f"Error getting predictions: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/cohort/pattern-summary')
    def get_pattern_summary():
        """Get summary of collection patterns"""
        try:
            # Get filter parameters
            weeks = request.args.get('weeks', 12, type=int)
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            # Create analyzer with appropriate lookback period
            if start_date and end_date:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                weeks = int((end - start).days / 7)
                filtered_analyzer = SalesCohortAnalyzer(lookback_weeks=weeks, start_date=start, end_date=end)
            else:
                filtered_analyzer = SalesCohortAnalyzer(lookback_weeks=weeks)
            analysis = filtered_analyzer.analyze_collection_patterns()
            
            summary = {
                'average_pattern': analysis.get('average_pattern', {}),
                'trends': analysis.get('trends', {}),
                'summary_stats': analysis.get('summary', {})
            }
            
            return jsonify({
                'success': True,
                'data': summary
            })
        except Exception as e:
            logger.error(f"Error getting pattern summary: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    return app