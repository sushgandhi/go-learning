import { useState, useEffect } from 'react';
import { TextField, Select, MenuItem, FormControl, InputLabel } from '@mui/material';

const platforms = {
  AWS: ['S3', 'ECS'],
  Azure: ['BlobStorage', 'OpenAI'],
  GCP: ['Vertex', 'GKE'],
};

function AddPlatform({ users, onPlatformAdded, handleClose }) {
  const [selectedUser, setSelectedUser] = useState('');
  const [cid, setCid] = useState('');
  const [selectedPlatform, setSelectedPlatform] = useState('');
  const [services, setServices] = useState([]);
  const [selectedService, setSelectedService] = useState('');

  useEffect(() => {
    if (selectedPlatform && platforms[selectedPlatform]) {
      setServices(platforms[selectedPlatform]);
    } else {
      setServices([]);
    }
  }, [selectedPlatform]);

  const handleSubmit = (event) => {
    event.preventDefault();
    const newPlatform = { user: selectedUser, cid, platform: selectedPlatform, service: selectedService };
    onPlatformAdded(newPlatform);
    handleClose();
  };

  return (
    <form onSubmit={handleSubmit}>
      <FormControl fullWidth>
        <InputLabel>User</InputLabel>
        <Select value={selectedUser} onChange={(e) => setSelectedUser(e.target.value)}>
          {users.map((user) => (
            <MenuItem key={user.id} value={user.id}>{user.name}</MenuItem>
          ))}
        </Select>
      </FormControl>
      <TextField label="CID" value={cid} onChange={(e) => setCid(e.target.value)} fullWidth />
      <FormControl fullWidth>
        <InputLabel>Platform</InputLabel>
        <Select value={selectedPlatform} onChange={(e) => setSelectedPlatform(e.target.value)}>
          {Object.keys(platforms).map((platform) => (
            <MenuItem key={platform} value={platform}>{platform}</MenuItem>
          ))}
        </Select>
      </FormControl>
      <FormControl fullWidth>
        <InputLabel>Service</InputLabel>
        <Select value={selectedService} onChange={(e) => setSelectedService(e.target.value)}>
          {services.map((service) => (
            <MenuItem key={service} value={service}>{service}</MenuItem>
          ))}
        </Select>
      </FormControl>
      <button type="submit">Add Platform</button>
    </form>
  );
}

export default AddPlatform;
