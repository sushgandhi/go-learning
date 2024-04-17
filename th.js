import { useState, useEffect } from 'react';
import { TextField, Select, MenuItem, FormControl, InputLabel, Chip } from '@mui/material';

const platforms = {
  AWS: ['S3', 'ECS'],
  Azure: ['BlobStorage', 'OpenAI'],
  GCP: ['Vertex', 'GKE'],
};

function AddPlatform({ onPlatformAdded, handleClose }) {
  const [selectedUser, setSelectedUser] = useState('');
  const [cid, setCid] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState([]);
  const [services, setServices] = useState([]);
  const [selectedService, setSelectedService] = useState('');

  useEffect(() => {
    if (selectedPlatforms.length > 0) {
      setServices(selectedPlatforms.flatMap(platform => platforms[platform] || []));
    } else {
      setServices([]);
    }
  }, [selectedPlatforms]);

  const handleSubmit = (event) => {
    event.preventDefault();
    const newPlatform = {
      user: selectedUser,
      cid,
      platforms: selectedPlatforms.map(platform => ({
        platformname: platform,
        services: services.map(service => ({
          servicename: service,
          serviceversion: "20220311"
        }))
      }))
    };

    // ... rest of the handleSubmit function
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* ... rest of the form */}
      <FormControl fullWidth>
        <InputLabel>Platform</InputLabel>
        <Select
          multiple
          value={selectedPlatforms}
          onChange={(e) => setSelectedPlatforms(e.target.value)}
          renderValue={(selected) => (
            <div>
              {selected.map((value) => (
                <Chip key={value} label={value} />
              ))}
            </div>
          )}
        >
          {Object.keys(platforms).map((platform) => (
            <MenuItem key={platform} value={platform}>{platform}</MenuItem>
          ))}
        </Select>
      </FormControl>
      {/* ... rest of the form */}
    </form>
  );
}

export default AddPlatform;
