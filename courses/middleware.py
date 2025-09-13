from django.utils.deprecation import MiddlewareMixin
from django.db import transaction
from .models import Visitor
import logging

logger = logging.getLogger(__name__)


class VisitorTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track website visitors and page views.
    """
    
    def process_request(self, request):
        """Store request information for later use in process_response"""
        # Skip tracking for certain paths
        skip_paths = [
            '/admin/',
            '/static/',
            '/media/',
            '/favicon.ico',
            '/robots.txt',
        ]
        
        if any(request.path.startswith(path) for path in skip_paths):
            return None
            
        # Store request info for use in process_response
        request._visitor_tracking = {
            'ip_address': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'referer': request.META.get('HTTP_REFERER', ''),
            'path': request.path,
            'query_string': request.META.get('QUERY_STRING', ''),
            'method': request.method,
            'user': request.user if request.user.is_authenticated else None,
            'session_key': request.session.session_key or '',
        }
        
        return None
    
    def process_response(self, request, response):
        """Track the visit after the response is generated"""
        if not hasattr(request, '_visitor_tracking'):
            return response
            
        try:
            # Only track successful responses
            if 200 <= response.status_code < 400:
                visitor_data = request._visitor_tracking.copy()
                visitor_data['status_code'] = response.status_code
                
                # Use atomic transaction to avoid blocking the response
                with transaction.atomic():
                    Visitor.objects.create(**visitor_data)
                    
        except Exception as e:
            # Log the error but don't break the response
            logger.error(f"Error tracking visitor: {e}")
            
        return response
    
    def get_client_ip(self, request):
        """Get the client's IP address, considering proxy headers"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
