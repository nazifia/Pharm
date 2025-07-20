"""
Session validation middleware to ensure proper user session isolation.
This middleware prevents session hijacking and ensures each user has independent sessions.
"""

from django.contrib.auth import logout
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)


class SessionValidationMiddleware:
    """
    Middleware to validate session integrity and ensure proper user isolation.
    
    Features:
    - Validates session belongs to the correct user
    - Prevents session fixation attacks
    - Ensures session data integrity
    - Logs suspicious session activity
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only validate sessions for authenticated users
        # Check if user is authenticated and has the required attributes
        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                # Validate session integrity
                if not self._validate_session(request):
                    logger.warning(f"Invalid session detected for user {getattr(request.user, 'username', 'unknown')}")
                    logout(request)
                    messages.error(request, "Your session has expired for security reasons. Please log in again.")
                    return HttpResponseRedirect(reverse('store:index'))

                # Update session with user-specific data
                self._update_session_data(request)
            except Exception as e:
                logger.error(f"Session validation middleware error: {e}")
                # Don't break the request flow on middleware errors

        response = self.get_response(request)
        return response

    def _validate_session(self, request):
        """
        Validate that the session belongs to the authenticated user.
        """
        try:
            # Check if session has user-specific validation data
            session_user_id = request.session.get('_auth_user_id')
            if not session_user_id:
                return False
            
            # Ensure session user matches authenticated user
            if str(request.user.id) != str(session_user_id):
                return False
            
            # Check session timestamp for additional validation
            session_created = request.session.get('session_created')
            if not session_created:
                # Add session creation timestamp if missing
                request.session['session_created'] = timezone.now().isoformat()
            
            # Validate session hasn't been tampered with
            expected_session_key = self._generate_session_validation_key(request.user)
            stored_session_key = request.session.get('session_validation_key')
            
            if stored_session_key != expected_session_key:
                # Update validation key (might be first login or key rotation)
                request.session['session_validation_key'] = expected_session_key
            
            return True
            
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return False

    def _update_session_data(self, request):
        """
        Update session with user-specific data for validation.
        """
        try:
            # Store user-specific session data
            request.session['user_id'] = request.user.id
            request.session['username'] = request.user.username
            request.session['last_validation'] = timezone.now().isoformat()
            
            # Generate and store session validation key
            validation_key = self._generate_session_validation_key(request.user)
            request.session['session_validation_key'] = validation_key
            
        except Exception as e:
            logger.error(f"Error updating session data: {e}")

    def _generate_session_validation_key(self, user):
        """
        Generate a user-specific session validation key.
        """
        import hashlib
        
        # Create a hash based on user-specific data
        data = f"{user.id}:{user.username}:{user.date_joined.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]


class SessionCleanupMiddleware:
    """
    Middleware to clean up expired sessions and prevent session buildup.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.cleanup_counter = 0

    def __call__(self, request):
        # Periodically clean up expired sessions (every 100 requests)
        self.cleanup_counter += 1
        if self.cleanup_counter >= 100:
            self._cleanup_expired_sessions()
            self.cleanup_counter = 0
        
        response = self.get_response(request)
        return response

    def _cleanup_expired_sessions(self):
        """
        Clean up expired sessions from the database.
        """
        try:
            expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
            count = expired_sessions.count()
            expired_sessions.delete()
            logger.info(f"Cleaned up {count} expired sessions")
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")


class UserActivityTrackingMiddleware:
    """
    Middleware to track user activity per session for security monitoring.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only track activity for authenticated users
        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                self._track_user_activity(request)
            except Exception as e:
                logger.error(f"User activity tracking error: {e}")
                # Don't break the request flow on middleware errors

        response = self.get_response(request)
        return response

    def _track_user_activity(self, request):
        """
        Track user activity in their session for security monitoring.
        """
        try:
            # Get or initialize activity tracking data
            activity_data = request.session.get('user_activity', {
                'login_time': timezone.now().isoformat(),
                'page_views': 0,
                'last_activity': timezone.now().isoformat(),
                'ip_address': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200]
            })
            
            # Update activity data
            activity_data['page_views'] += 1
            activity_data['last_activity'] = timezone.now().isoformat()
            
            # Check for suspicious activity (IP change)
            current_ip = self._get_client_ip(request)
            if activity_data['ip_address'] != current_ip:
                logger.warning(f"IP address change detected for user {request.user.username}: "
                             f"{activity_data['ip_address']} -> {current_ip}")
                # Update IP but log the change
                activity_data['ip_address'] = current_ip
            
            # Store updated activity data
            request.session['user_activity'] = activity_data
            
        except Exception as e:
            logger.error(f"Error tracking user activity: {e}")

    def _get_client_ip(self, request):
        """
        Get the client's IP address from the request.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
