"""
Standard API response format helpers.
"""
from rest_framework.response import Response
from rest_framework import status


def success_response(message, data=None, status_code=status.HTTP_200_OK):
    """
    Return a success response.
    """
    response = {
        'status': 'success',
        'message': message,
    }
    if data is not None:
        response['data'] = data
    return Response(response, status=status_code)


def error_response(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Return an error response.
    """
    response = {
        'status': 'error',
        'message': message,
    }
    if errors is not None:
        response['errors'] = errors
    return Response(response, status=status_code)


def created_response(message, data=None):
    """
    Return a created (201) response.
    """
    return success_response(message, data, status.HTTP_201_CREATED)


def not_found_response(message="Resource not found"):
    """
    Return a not found (404) response.
    """
    return error_response(message, status_code=status.HTTP_404_NOT_FOUND)


def unauthorized_response(message="Authentication required"):
    """
    Return an unauthorized (401) response.
    """
    return error_response(message, status_code=status.HTTP_401_UNAUTHORIZED)


def forbidden_response(message="Permission denied"):
    """
    Return a forbidden (403) response.
    """
    return error_response(message, status_code=status.HTTP_403_FORBIDDEN)
