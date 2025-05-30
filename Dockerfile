FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \ # installs system packages for GUI and networking
    wget \
    netcat-traditional \
    gnupg \
    curl \
    unzip \
    xvfb \
    libgconf-2-4 \
    libxss1 \
    libnss3 \
    libnspr4 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    xdg-utils \
    fonts-liberation \
    dbus \
    xauth \
    xvfb \
    x11vnc \
    tigervnc-tools \
    supervisor \
    net-tools \
    procps \
    git \
    python3-numpy \
    fontconfig \
    fonts-dejavu \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    && rm -rf /var/lib/apt/lists/*

# Install noVNC
RUN git clone https://github.com/novnc/noVNC.git /opt/novnc \ # clones noVNC for browser based VNC access
    && git clone https://github.com/novnc/websockify /opt/novnc/utils/websockify \
    && ln -s /opt/novnc/vnc.html /opt/novnc/index.html

# Set platform for ARM64 compatibility
ARG TARGETPLATFORM=linux/amd64

# Set up working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt . # copies dependency list for installation
RUN pip install --no-cache-dir -r requirements.txt # installs python dependencies without caching

# Install patchright and browsers with system dependencies
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-patchright # points patchright to store its browsers
RUN patchright install --with-deps chromium # installs chromium browser with dependencies via patchright
RUN patchright install-deps # sets up system dependencies for patchright browsers

# Copy the application code
COPY . . # copies the application source into the container

# Set environment variables
ENV PYTHONUNBUFFERED=1 # ensures python output is sent straight to logs
ENV BROWSER_USE_LOGGING_LEVEL=info # sets default logging verbosity for browser tools
ENV CHROME_PATH=/ms-playwright/chromium-*/chrome-linux/chrome # path where chromium binary is installed
ENV ANONYMIZED_TELEMETRY=false # disables telemetry to avoid data collection
ENV DISPLAY=:99 # sets X display number for headless operations
ENV RESOLUTION=1920x1080x24 # sets resolution depth for virtual display
ENV VNC_PASSWORD=vncpassword # password for remote VNC access
ENV CHROME_PERSISTENT_SESSION=true # reuses chrome session for improved speed
ENV RESOLUTION_WIDTH=1920 # width for VNC and browser display
ENV RESOLUTION_HEIGHT=1080 # height for VNC and browser display

# Set up supervisor configuration
RUN mkdir -p /var/log/supervisor # creates log directory for supervisord
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf # copies supervisor process configuration

EXPOSE 7788 6080 5901

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
