FROM node:18-alpine

WORKDIR /app

# Install curl for health checks
RUN apk --no-cache add curl

# Copy package.json and package-lock.json first for better caching
COPY package.json package-lock.json ./
RUN npm ci

# Copy the rest of the application
COPY . .

# Expose the port the app runs on
EXPOSE 3000

# Command to run the application with hot reload for development
CMD ["npm", "start"]
