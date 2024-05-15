const express = require('express');
const path = require('path');
const app = express();
app.use(express.static(path.join(__dirname, 'build')));
app.get('/*', function (req, res) {
  res.sendFile(path.join(__dirname, 'build', 'index.html'));
});
app.listen(80);

##docker

  # Stage 1 - the build process
FROM node:14 as build-deps
WORKDIR /usr/src/app
COPY package*.json ./
RUN npm install
COPY . ./
RUN npm run build

# Stage 2 - the production environment
FROM node:14
WORKDIR /usr/src/app
COPY --from=build-deps /usr/src/app/build ./build
COPY server.js ./
RUN npm install express
EXPOSE 80
CMD [ "node", "server.js" ]



docker build -t my-react-app .
docker run -p 80:80 my-react-app


packag.json --good to do

"scripts": {
  "start": "node server.js",
  "build": "react-scripts build",
  "test": "react-scripts test",
  "eject": "react-scripts eject"
}
