import { useState } from 'react';
import { TextField, InputAdornment, IconButton } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';

function SearchBar() {
  const [username, setUsername] = useState('');
  const [userDetails, setUserDetails] = useState(null);

  const handleSearch = async () => {
    try {
      const response = await fetch(`http://localhost:8080/api/v1/users/${username}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setUserDetails(data);
    } catch (error) {
      console.error('Failed to fetch user details:', error);
    }
  };

  return (
    <TextField
      label="Username"
      value={username}
      onChange={e => setUsername(e.target.value)}
      InputProps={{
        endAdornment: (
          <InputAdornment position="end">
            <IconButton onClick={handleSearch}>
              <SearchIcon />
            </IconButton>
          </InputAdornment>
        ),
      }}
    />
  );
}

export default SearchBar;
