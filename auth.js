// src/authService.ts

import { UserManager } from 'oidc-client';

const config = {
  authority: 'https://your-oidc-provider.com',
  client_id: 'your-client-id',
  redirect_uri: 'http://localhost:3000/callback',
  response_type: 'code',
  scope: 'openid profile email',
};

const userManager = new UserManager(config);

export default userManager;


// src/App.tsx

import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Route, Redirect } from 'react-router-dom';
import userManager from './authService';
import Home from './components/Home/Home';
import UserDetails from './components/UserDetails/UserDetails';
import AddUser from './components/AddUser/AddUser';
import Callback from './components/Callback/Callback';

const PrivateRoute = ({ component: Component, ...rest }) => {
  const [user, setUser] = useState(null);

  useEffect(() => {
    userManager.getUser().then(setUser);
  }, []);

  return (
    <Route
      {...rest}
      render={props =>
        user ? (
          <Component {...props} />
        ) : (
          <Redirect to="/callback" />
        )
      }
    />
  );
};

const App = () => {
  useEffect(() => {
    userManager.getUser().then(user => {
      if (!user) {
        userManager.signinRedirect();
      }
    });
  }, []);

  return (
    <Router>
      <PrivateRoute path="/" exact component={Home} />
      <PrivateRoute path="/userdetails" component={UserDetails} />
      <PrivateRoute path="/adduser" component={AddUser} />
      <Route path="/callback" component={Callback} />
    </Router>
  );
};

export default App;

// src/components/Callback/Callback.tsx

import React, { useEffect } from 'react';
import { useHistory } from 'react-router-dom';
import userManager from '../../authService';

const Callback = () => {
  const history = useHistory();

  useEffect(() => {
    userManager.signinRedirectCallback().then(user => {
      console.log('Logged in as', user.profile);
      // Redirect the user to the main page of your application
      history.push('/');
    }).catch(err => {
      console.error(err);
      // Handle errors, e.g. by showing an error message to the user
    });
  }, [history]);

  return <div>Loading...</div>;
};

export default Callback;


