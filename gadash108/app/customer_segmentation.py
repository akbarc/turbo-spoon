"""
Customer Segmentation Dashboard Routes
Provides RFM analysis, customer segments, and actionable insights
"""

from flask import Flask, render_template, jsonify, request, Response
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import io
import csv
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def register_segmentation_routes(app, db_connection=None):
    """Register customer segmentation routes with the Flask app"""

    @app.route('/customer-segmentation')
    def customer_segmentation_page():
        """Main customer segmentation dashboard"""
        return render_template('customer_segmentation.html')

    @app.route('/api/segmentation/overview')
    def get_segmentation_overview():
        """Get comprehensive segmentation overview"""
        try:
            from modules.segmentation.segment_engine import SegmentationEngine

            engine = SegmentationEngine(db_connection)
            overview = engine.get_overview()

            return jsonify({
                'success': True,
                'data': overview
            })
        except Exception as e:
            logger.error(f"Error in segmentation overview: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/segmentation/rfm-analysis')
    def get_rfm_analysis():
        """Get detailed RFM analysis"""
        try:
            from modules.segmentation.segment_engine import SegmentationEngine

            # Get filter parameters
            min_revenue = request.args.get('min_revenue', 0, type=float)
            days_back = request.args.get('days_back', 365, type=int)

            engine = SegmentationEngine(db_connection)
            rfm_data = engine.calculate_rfm_scores(
                min_revenue=min_revenue,
                days_back=days_back
            )

            # Calculate distributions
            distribution = {
                'recency': {
                    '0-30': len(rfm_data[rfm_data['recency'] <= 30]),
                    '31-60': len(rfm_data[(rfm_data['recency'] > 30) & (rfm_data['recency'] <= 60)]),
                    '61-90': len(rfm_data[(rfm_data['recency'] > 60) & (rfm_data['recency'] <= 90)]),
                    '90+': len(rfm_data[rfm_data['recency'] > 90])
                },
                'frequency': {
                    '1-5': len(rfm_data[rfm_data['frequency'] <= 5]),
                    '6-10': len(rfm_data[(rfm_data['frequency'] > 5) & (rfm_data['frequency'] <= 10)]),
                    '11-20': len(rfm_data[(rfm_data['frequency'] > 10) & (rfm_data['frequency'] <= 20)]),
                    '20+': len(rfm_data[rfm_data['frequency'] > 20])
                },
                'segments': rfm_data.groupby('segment').size().to_dict()
            }

            # Top customers by RFM score
            top_customers = rfm_data.nlargest(20, 'rfm_numeric')[
                ['customer_id', 'company_name', 'segment', 'recency',
                 'frequency', 'monetary', 'rfm_score', 'clv_estimate']
            ].to_dict('records')

            return jsonify({
                'success': True,
                'data': {
                    'total_customers': len(rfm_data),
                    'distribution': distribution,
                    'top_customers': top_customers,
                    'avg_metrics': {
                        'recency': float(rfm_data['recency'].mean()),
                        'frequency': float(rfm_data['frequency'].mean()),
                        'monetary': float(rfm_data['monetary'].mean())
                    }
                }
            })
        except Exception as e:
            logger.error(f"Error in RFM analysis: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/segmentation/segment-details/<segment>')
    def get_segment_details(segment):
        """Get detailed information for a specific segment"""
        try:
            from modules.segmentation.segment_engine import SegmentationEngine

            engine = SegmentationEngine(db_connection)
            segment_data = engine.get_segment_details(segment)

            if segment_data is None:
                return jsonify({
                    'success': False,
                    'error': f'Segment {segment} not found'
                }), 404

            return jsonify({
                'success': True,
                'data': segment_data
            })
        except Exception as e:
            logger.error(f"Error getting segment details for {segment}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/segmentation/customer-list')
    def get_segmented_customers():
        """Get filtered customer list with segments"""
        try:
            from modules.segmentation.segment_engine import SegmentationEngine

            # Get filter parameters
            segment_filter = request.args.get('segment')
            min_balance = request.args.get('min_balance', 0, type=float)
            sort_by = request.args.get('sort_by', 'monetary_desc')
            limit = request.args.get('limit', 100, type=int)
            offset = request.args.get('offset', 0, type=int)

            engine = SegmentationEngine(db_connection)
            customers = engine.get_customer_list(
                segment_filter=segment_filter,
                min_balance=min_balance,
                sort_by=sort_by,
                limit=limit,
                offset=offset
            )

            return jsonify({
                'success': True,
                'data': {
                    'customers': customers['data'],
                    'total': customers['total'],
                    'filtered': customers['filtered']
                }
            })
        except Exception as e:
            logger.error(f"Error getting segmented customers: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/segmentation/actions')
    def get_segment_actions():
        """Get actionable recommendations per segment"""
        try:
            from modules.segmentation.segment_engine import SegmentationEngine

            engine = SegmentationEngine(db_connection)
            actions = engine.get_actionable_recommendations()

            return jsonify({
                'success': True,
                'data': actions
            })
        except Exception as e:
            logger.error(f"Error getting segment actions: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/segmentation/trends')
    def get_segmentation_trends():
        """Get segment migration and trends over time"""
        try:
            from modules.segmentation.segment_engine import SegmentationEngine

            # Get time period
            period = request.args.get('period', '6months')

            engine = SegmentationEngine(db_connection)
            trends = engine.calculate_segment_trends(period)

            return jsonify({
                'success': True,
                'data': trends
            })
        except Exception as e:
            logger.error(f"Error getting segmentation trends: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/segmentation/at-risk')
    def get_at_risk_customers():
        """Get high-value at-risk customers"""
        try:
            from modules.segmentation.segment_engine import SegmentationEngine

            # Get parameters
            risk_threshold = request.args.get('threshold', 0.7, type=float)
            min_value = request.args.get('min_value', 10000, type=float)

            engine = SegmentationEngine(db_connection)
            at_risk = engine.identify_at_risk_customers(
                risk_threshold=risk_threshold,
                min_value=min_value
            )

            return jsonify({
                'success': True,
                'data': {
                    'customers': at_risk,
                    'total_at_risk_value': sum(c['monetary'] for c in at_risk),
                    'count': len(at_risk)
                }
            })
        except Exception as e:
            logger.error(f"Error getting at-risk customers: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/segmentation/export')
    def export_segmentation():
        """Export segmentation data"""
        try:
            from modules.segmentation.segment_engine import SegmentationEngine

            # Get export parameters
            format_type = request.args.get('format', 'csv')
            segment_filter = request.args.get('segment')
            include_metrics = request.args.get('include_metrics', 'true').lower() == 'true'

            engine = SegmentationEngine(db_connection)

            if segment_filter:
                data = engine.get_segment_details(segment_filter)['customers']
            else:
                rfm_data = engine.calculate_rfm_scores()
                data = rfm_data.to_dict('records')

            if format_type == 'csv':
                # Create CSV
                output = io.StringIO()
                if data:
                    writer = csv.DictWriter(output, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)

                response = Response(
                    output.getvalue(),
                    mimetype='text/csv',
                    headers={
                        'Content-Disposition': f'attachment; filename=customer_segments_{datetime.now().strftime("%Y%m%d")}.csv'
                    }
                )
                return response

            elif format_type == 'json':
                return jsonify({
                    'export_date': datetime.now().isoformat(),
                    'total_records': len(data),
                    'segments': data
                })

            else:
                return jsonify({'error': 'Unsupported export format'}), 400

        except Exception as e:
            logger.error(f"Error exporting segmentation: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/segmentation/health-check')
    def segmentation_health_check():
        """Check segmentation system health"""
        try:
            from modules.segmentation.segment_engine import SegmentationEngine

            engine = SegmentationEngine(db_connection)
            health = engine.health_check()

            return jsonify({
                'success': True,
                'data': health
            })
        except Exception as e:
            logger.error(f"Error in segmentation health check: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'status': 'unhealthy'
            }), 500