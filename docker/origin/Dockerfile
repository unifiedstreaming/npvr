ARG UPSTREAM_DOCKER_IMAGE=docker.io/unifiedstreaming/origin:1.13.0

FROM $UPSTREAM_DOCKER_IMAGE

# Overwite config
RUN rm -f /etc/apache2/conf.d/*

COPY conf.d /etc/apache2/conf.d

# Copy entrypoint
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Copy webpage
COPY html /var/www/unified-origin/

EXPOSE 80

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

CMD ["-D", "FOREGROUND"]