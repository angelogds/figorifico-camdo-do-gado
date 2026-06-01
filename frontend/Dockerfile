# Build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install --legacy-peer-deps
COPY . .
RUN npm run build

# Runtime stage
FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production
RUN npm install -g serve
COPY --from=build /app/build /app/build
# Railway provides PORT. Default to 3000 locally.
CMD ["sh", "-c", "serve -s build -l ${PORT:-3000}"]
