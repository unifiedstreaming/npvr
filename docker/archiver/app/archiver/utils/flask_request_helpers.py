def request_wants_json(request):
    """
    Helper function to check if request includes accept header application/json
    """
    best = request.accept_mimetypes.best_match(
        ["application/json", "text/html"]
    )
    return (
        best == "application/json"
        and request.accept_mimetypes[best]
        > request.accept_mimetypes["text/html"]
    )
