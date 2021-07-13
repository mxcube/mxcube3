import os
import ruamel.yaml


class FlaskConfig:
    SECRET_KEY = b"o`\xb5\xa5\xc2\x8c\xb2\x8c-?\xe0,/i#c"
    SESSION_TYPE = "redis"
    SESSION_KEY_PREFIX = "mxcube:session:"
    DEBUG: False
    STREAMED_VIDEO: True
    ALLOWED_CORS_ORIGINS = "*"


class AppConfig:
    VIDEO_FORMAT = "MPEG1"


class Config:
    flask = FlaskConfig()
    app = AppConfig()

    def __init__(self, fpath=None):
        with open(fpath) as f:
            config = ruamel.yaml.load(f.read(), ruamel.yaml.RoundTripLoader)

            for key, value in config["server"].items():
                setattr(self.flask, key, value)

            for key, value in config["mxcube"].items():
                setattr(self.app, key, value)
