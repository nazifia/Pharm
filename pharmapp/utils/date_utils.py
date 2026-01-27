"""
Date utility functions for consistent date handling across the application.
"""

from datetime import datetime, date
from django.utils.dateparse import parse_date
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def parse_date_string(date_string):
    """
    Parse a date string in various formats and return a date object.
    
    Args:
        date_string (str): Date string in formats like 'YYYY-MM-DD', 'DD/MM/YYYY', etc.
        
    Returns:
        date: Parsed date object or None if parsing fails
    """
    if not date_string or not isinstance(date_string, str):
        return None
    
    date_string = date_string.strip()
    if not date_string:
        return None
    
    # List of common date formats to try
    date_formats = [
        '%Y-%m-%d',      # 2023-12-25
        '%d/%m/%Y',      # 25/12/2023
        '%m/%d/%Y',      # 12/25/2023
        '%d-%m-%Y',      # 25-12-2023
        '%Y/%m/%d',      # 2023/12/25
        '%d.%m.%Y',      # 25.12.2023
    ]
    
    # First try Django's built-in parser
    try:
        parsed_date = parse_date(date_string)
        if parsed_date:
            return parsed_date
    except (ValueError, TypeError):
        pass
    
    # Try different formats
    for date_format in date_formats:
        try:
            parsed_datetime = datetime.strptime(date_string, date_format)
            return parsed_datetime.date()
        except ValueError:
            continue
    
    logger.warning(f"Could not parse date string: {date_string}")
    return None


def filter_queryset_by_date(queryset, date_field, date_string):
    """
    Filter a queryset by a date field using a date string.

    Args:
        queryset: Django queryset to filter
        date_field (str): Name of the date field to filter on
        date_string (str): Date string to parse and filter by

    Returns:
        queryset: Filtered queryset or original queryset if parsing fails
    """
    parsed_date = parse_date_string(date_string)
    if parsed_date:
        # Handle both DateField and DateTimeField
        # If the field already has __date suffix, use it directly
        # If it's a DateTimeField without __date suffix, add __date to filter by date part
        # If it's a DateField (simple field name), use it directly
        if '__date' in date_field:
            # Already has __date suffix (e.g., 'created_at__date')
            filter_kwargs = {date_field: parsed_date}
        elif date_field.endswith('__date'):
            # Ends with __date (e.g., 'created_at__date')
            filter_kwargs = {date_field: parsed_date}
        else:
            # Try to determine field type from the model
            try:
                model = queryset.model
                field = model._meta.get_field(date_field)
                from django.db.models import DateTimeField
                if isinstance(field, DateTimeField):
                    # DateTimeField - filter by date part
                    filter_kwargs = {f"{date_field}__date": parsed_date}
                else:
                    # DateField or other - use directly
                    filter_kwargs = {date_field: parsed_date}
            except Exception:
                # Fallback: assume fields with underscores are DateTimeFields
                if '_' in date_field:
                    filter_kwargs = {f"{date_field}__date": parsed_date}
                else:
                    filter_kwargs = {date_field: parsed_date}

        return queryset.filter(**filter_kwargs)

    return queryset


def filter_queryset_by_date_range(queryset, date_field, date_from_string, date_to_string):
    """
    Filter a queryset by a date range using date strings.
    
    Args:
        queryset: Django queryset to filter
        date_field (str): Name of the date field to filter on
        date_from_string (str): Start date string
        date_to_string (str): End date string
        
    Returns:
        queryset: Filtered queryset
    """
    if date_from_string:
        date_from = parse_date_string(date_from_string)
        if date_from:
            # Handle both DateField and DateTimeField
            if '__date' not in date_field:
                filter_kwargs = {f"{date_field}__date__gte": date_from}
            else:
                filter_kwargs = {f"{date_field}__gte": date_from}
            queryset = queryset.filter(**filter_kwargs)
    
    if date_to_string:
        date_to = parse_date_string(date_to_string)
        if date_to:
            # Handle both DateField and DateTimeField
            if '__date' not in date_field:
                filter_kwargs = {f"{date_field}__date__lte": date_to}
            else:
                filter_kwargs = {f"{date_field}__lte": date_to}
            queryset = queryset.filter(**filter_kwargs)
    
    return queryset


def get_date_filter_context(request, date_param='date'):
    """
    Get date filter context from request parameters.
    
    Args:
        request: Django request object
        date_param (str): Name of the date parameter in GET request
        
    Returns:
        dict: Context with parsed date and original string
    """
    date_string = request.GET.get(date_param, '').strip()
    parsed_date = parse_date_string(date_string) if date_string else None
    
    return {
        'date_string': date_string,
        'parsed_date': parsed_date,
        'is_valid_date': parsed_date is not None
    }


def get_date_range_filter_context(request, date_from_param='date_from', date_to_param='date_to'):
    """
    Get date range filter context from request parameters.
    
    Args:
        request: Django request object
        date_from_param (str): Name of the start date parameter
        date_to_param (str): Name of the end date parameter
        
    Returns:
        dict: Context with parsed dates and original strings
    """
    date_from_string = request.GET.get(date_from_param, '').strip()
    date_to_string = request.GET.get(date_to_param, '').strip()
    
    date_from = parse_date_string(date_from_string) if date_from_string else None
    date_to = parse_date_string(date_to_string) if date_to_string else None
    
    return {
        'date_from_string': date_from_string,
        'date_to_string': date_to_string,
        'date_from': date_from,
        'date_to': date_to,
        'has_date_filter': bool(date_from or date_to)
    }


def format_date_for_input(date_obj):
    """
    Format a date object for HTML date input (YYYY-MM-DD format).
    
    Args:
        date_obj: Date object or None
        
    Returns:
        str: Formatted date string or empty string
    """
    if date_obj:
        if isinstance(date_obj, datetime):
            return date_obj.date().strftime('%Y-%m-%d')
        elif isinstance(date_obj, date):
            return date_obj.strftime('%Y-%m-%d')
    return ''


def get_today():
    """
    Get today's date in the application's timezone.
    
    Returns:
        date: Today's date
    """
    return timezone.now().date()


def is_valid_date_string(date_string):
    """
    Check if a date string can be parsed.
    
    Args:
        date_string (str): Date string to validate
        
    Returns:
        bool: True if the date string is valid, False otherwise
    """
    return parse_date_string(date_string) is not None
