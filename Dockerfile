FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 1. Install Linux system libraries (OpenGL, glib, Pango for WeasyPrint & OpenCV)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# 2. Install triton (Linux GPU kernel for SAM 3)
RUN pip install triton

# 3. Clone and install SAM 3 from official Meta repository
RUN git clone https://github.com/facebookresearch/sam3.git /app/sam3-repo && \
    pip install -e /app/sam3-repo

# 4. Copy project definition and install dependencies
COPY pyproject.toml /app/
RUN pip install "numpy>=1.26,<2" "opencv-python>=4.10.0,<5.0.0" "scipy>=1.13.0,<1.14.0" && \
    pip install -e .

# 5. Copy project source code
COPY backend/ /app/backend/
COPY samples/ /app/samples/

# 6. Volumes for persistent weights and outputs
VOLUME ["/app/weights", "/app/output"]

EXPOSE 8000

# Default command: Runs the facade segmentation pipeline
CMD ["python", "backend/demo_segment.py", "--image", "samples/image.png", "--output", "output/"]
