class PostcardData:
    def __init__(self):
        self.user = None
        self.subject = None
        self.item = None
        self.lines = ["", "", "", ""]

    @classmethod
    def from_request(cls, request):
        return request.session.setdefault("postcard", cls())

    @classmethod
    def delete(cls, request):
        request.session.pop("postcard", None)
