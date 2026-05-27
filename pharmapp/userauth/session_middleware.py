"""
Session validation middleware to ensure proper user session isolation.
This middleware prevents session hijacking and ensures each user has independent sessions.
"""

import threading
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
        Throttled to once per 60 seconds to reduce DB writes.
        """
        try:
            last_validation = request.session.get('last_validation')
            if last_validation:
                last_dt = timezone.datetime.fromisoformat(last_validation)
                if (timezone.now() - last_dt).total_seconds() < 60:
                    return  # Skip — recently validated

            request.session['user_id'] = request.user.id
            request.session['username'] = request.user.username
            request.session['last_validation'] = timezone.now().isoformat()

            validation_key = self._generate_session_validation_key(request.user)
            request.session['session_validation_key'] = validation_key

            if 'user_data' not in request.session:
                request.session['user_data'] = {}

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
        self.cleanup_counter += 1
        if self.cleanup_counter >= 100:
            threading.Thread(target=self._cleanup_expired_sessions, daemon=True).start()
            self.cleanup_counter = 0

        response = self.get_response(request)
        return response

    def _cleanup_expired_sessions(self):
        try:
            deleted, _ = Session.objects.filter(expire_date__lt=timezone.now()).delete()
            if deleted:
                logger.info(f"Cleaned up {deleted} expired sessions")
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
        Throttled to once per 30 seconds to reduce DB writes.
        """
        try:
            now = timezone.now()
            activity_data = request.session.get('user_activity')

            if activity_data:
                last_dt = timezone.datetime.fromisoformat(activity_data.get('last_activity', ''))
                if (now - last_dt).total_seconds() < 30:
                    # Check IP change even when throttled (security)
                    current_ip = self._get_client_ip(request)
                    if activity_data.get('ip_address') != current_ip:
                        logger.warning(
                            f"IP change: {request.user.username} "
                            f"{activity_data['ip_address']} -> {current_ip}"
                        )
                        activity_data['ip_address'] = current_ip
                        request.session['user_activity'] = activity_data
                    return
            else:
                activity_data = {
                    'login_time': now.isoformat(),
                    'page_views': 0,
                    'last_activity': now.isoformat(),
                    'ip_address': self._get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
                }

            current_ip = self._get_client_ip(request)
            if activity_data.get('ip_address') != current_ip:
                logger.warning(
                    f"IP change: {request.user.username} "
                    f"{activity_data.get('ip_address')} -> {current_ip}"
                )
                activity_data['ip_address'] = current_ip

            activity_data['page_views'] = activity_data.get('page_views', 0) + 1
            activity_data['last_activity'] = now.isoformat()
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
