# Build the React application with its frontend dependencies.
FROM node:20-alpine AS build
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install --legacy-peer-deps
COPY frontend/ ./
RUN npm run build

# Serve only the compiled static files in production. The runtime does not
# invoke npm scripts, so it does not depend on /app/package.json being present.
FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
RUN npm install --global serve@14.2.1
COPY --from=build /app/frontend/build ./build
EXPOSE 3000
CMD ["sh", "-c", "serve -s build -l ${PORT:-3000}"]
