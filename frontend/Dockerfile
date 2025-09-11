# Use a Node.js base image
FROM node:20-alpine

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json (or yarn.lock)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# The port the app will run on
EXPOSE 5173

# The command is specified in docker-compose.yml to enable hot-reloading
# CMD ["npm", "run", "dev"]
