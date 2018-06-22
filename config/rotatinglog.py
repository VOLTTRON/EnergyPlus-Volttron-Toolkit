{
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'agent': {
            '()': 'volttron.platform.agent.utils.AgentFormatter',
        },
    },
    'handlers': {
        'rotating': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'maxBytes': 104857600,
            'formatter': 'agent',
            'filename': 'volttron.log',
            'encoding': 'utf-8',
            'backupCount': 3,
        },
    },
    'root': {
        'handlers': ['rotating'],
        'level': 'DEBUG',
    },
}
