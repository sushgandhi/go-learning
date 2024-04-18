import { useState, useEffect } from 'react';
import { Select, MenuItem, FormControl, InputLabel } from '@mui/material';
import axios from 'axios';

function UserPlatformSelector() {
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState('');
  const [platforms, setPlatforms] = useState([]);
  const [selectedPlatform, setSelectedPlatform] = useState('');
  const [secondUsers, setSecondUsers] = useState([]);
  const [selectedSecondUser, setSelectedSecondUser] = useState('');

  useEffect(() => {
    axios.get('/users')
      .then(response => setUsers(response.data))
      .catch(error => console.error(error));
  }, []);

  useEffect(() => {
    if (selectedUser) {
      axios.get(`/platforms/users/${selectedUser}`)
        .then(response => setPlatforms(response.data))
        .catch(error => console.error(error));
    }
  }, [selectedUser]);

  useEffect(() => {
    setSecondUsers(users.filter(user => user !== selectedUser));
  }, [selectedUser, users]);

  return (
    <div>
      <FormControl>
        <InputLabel>User</InputLabel>
        <Select value={selectedUser} onChange={e => setSelectedUser(e.target.value)}>
          {users.map(user => <MenuItem key={user} value={user}>{user}</MenuItem>)}
        </Select>
      </FormControl>

      <FormControl>
        <InputLabel>Platform</InputLabel>
        <Select value={selectedPlatform} onChange={e => setSelectedPlatform(e.target.value)}>
          {platforms.map(platform => <MenuItem key={platform} value={platform}>{platform}</MenuItem>)}
        </Select>
      </FormControl>

      <FormControl>
        <InputLabel>Second User</InputLabel>
        <Select value={selectedSecondUser} onChange={e => setSelectedSecondUser(e.target.value)}>
          {secondUsers.map(user => <MenuItem key={user} value={user}>{user}</MenuItem>)}
        </Select>
      </FormControl>
    </div>
  );
}

export default UserPlatformSelector;
