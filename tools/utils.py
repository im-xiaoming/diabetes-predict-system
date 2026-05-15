class AttrDict(dict):
    """ Create a dictionary that allows for attribute-style access. """
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self