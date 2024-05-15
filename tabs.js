import React from 'react';
import { useRoutes, useNavigate, useLocation } from 'react-router-dom';
import { Tabs } from 'antd';

import AddPlatformToUser from './AddPlatformToUser';
import AddPlatformToClient from './AddPlatformToClient';

const { TabPane } = Tabs;

const MyComponent = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleTabChange = (key: string) => {
    navigate(key);
  };

  const routes = useRoutes([
    { path: 'addPlatformToUser', element: <AddPlatformToUser /> },
    { path: 'addPlatformToClient', element: <AddPlatformToClient /> },
  ]);

  return (
    <>
      <Tabs defaultActiveKey="/addPlatformToUser" activeKey={location.pathname} onChange={handleTabChange}>
        <TabPane tab="Add Platform to User" key="/addPlatformToUser" />
        <TabPane tab="Add Platform to Client" key="/addPlatformToClient" />
      </Tabs>
      {routes}
    </>
  );
};

export default MyComponent;
