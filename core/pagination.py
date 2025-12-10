"""
Custom pagination classes.
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """
    Standard pagination with customizable page size.
    """
    page_size = 200
    page_size_query_param = 'page_size'
    max_page_size = 1000

    def get_paginated_response(self, data):
        return Response({
            'status': 'success',
            'data': {
                'pagination': {
                    'current_page': self.page.number,
                    'total_pages': self.page.paginator.num_pages,
                    'total_items': self.page.paginator.count,
                    'page_size': self.get_page_size(self.request),
                    'has_previous': self.page.has_previous(),
                    'has_next': self.page.has_next(),
                    'previous_page': self.page.previous_page_number() if self.page.has_previous() else None,
                    'next_page': self.page.next_page_number() if self.page.has_next() else None,
                },
                'results': data
            }
        })
