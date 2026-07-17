try:
    from dotenv import load_dotenv as _load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False
else:
    load_dotenv = _load_dotenv


