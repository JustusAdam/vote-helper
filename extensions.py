import time

def add_to(obj, name, value):

    if not hasattr(obj, name):
        setattr(obj, name, list(value))
    else:
        getattr(obj, name).extend(value)


class Meta:
    @staticmethod
    def requires(*requires):

        def inner(function):
            add_to(function, 'requires', requires)
            return function
        return inner

    @staticmethod
    def produces(*produces):
        def inner(function):
            add_to(function, 'produces', produces)
            return function
        return inner


@Meta.requires('cookies')
@Meta.produces('cookies')
def popupcheck(cookies):
    if cookies:
        cookies = cookies + ';'

    return cookies + 'POPUPCHECK={}'.format(int(time.time()) + 86400000)

print(dir(popupcheck))
