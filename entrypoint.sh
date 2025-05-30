#!/bin/bash

# Start supervisord in the foreground so Docker can monitor it    # ensures container shuts down cleanly when supervisord exits
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf    # launch supervisor with provided config
