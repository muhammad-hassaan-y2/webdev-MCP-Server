# Stage 1: bundle the widget (TypeScript + Three.js -> single HTML file).
# This stage's tools (Node, esbuild) are not needed at runtime - only the
# HTML file it produces gets copied into the final image.
FROM node:20-slim AS widget-build
WORKDIR /build
COPY package*.json ./
RUN npm install
COPY scripts ./scripts
COPY widget-src ./widget-src
RUN npm run build:widget

# Stage 2: the actual server. python3 is also needed at runtime, separately
# from the widget-build step above - it's what src/tutor_mcp/sandbox/run_python.py
# shells out to in order to run student code for code missions.
FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -e .

COPY --from=widget-build /build/widget-src/generated ./widget-src/generated

ENV PORT=3000
EXPOSE 3000
CMD ["python", "-m", "tutor_mcp.server"]
