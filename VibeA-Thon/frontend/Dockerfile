FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install -g pnpm@11.25.0
COPY pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["pnpm","start"]
