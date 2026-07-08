from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )


def paginate_queryset(request, queryset, *, serializer=None, many=False, context=None):
    """
    Paginate a queryset or list and return a DRF Response.
    Pass serializer=MySerializer to serialize page items (many=True).
    """
    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, request)
    if page is None:
        items = queryset
        if serializer is not None:
            items = serializer(items, many=many, context=context or {}).data
        return Response(items)

    if serializer is not None:
        data = serializer(page, many=many, context=context or {}).data
    else:
        data = page
    return paginator.get_paginated_response(data)
