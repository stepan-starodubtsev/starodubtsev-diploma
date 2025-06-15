// frontend/src/pages/LoginPage.jsx
import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { observer } from 'mobx-react-lite';
import {
    Container, Box, TextField, Button, Typography, CircularProgress, Alert
} from '@mui/material';
import authStore from '../stores/authStore';

const LoginPage = observer(() => {
    const navigate = useNavigate();
    const location = useLocation();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');

    const from = location.state?.from?.pathname || "/";

    const handleSubmit = async (event) => {
        event.preventDefault();
        try {
            await authStore.login(username, password);
            navigate(from, { replace: true });
        } catch (error) {
            console.error("Failed to login");
        }
    };

    return (
        <Container component="main" maxWidth="xs">
            <Box
                sx={{
                    marginTop: 8,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                }}
            >
                <Typography component="h1" variant="h5">
                    SIEM ZSU - Вхід
                </Typography>
                <Box component="form" onSubmit={handleSubmit} noValidate sx={{ mt: 1 }}>
                    <TextField
                        margin="normal"
                        required
                        fullWidth
                        id="username"
                        label="Ім'я користувача"
                        name="username"
                        autoComplete="username"
                        autoFocus
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                    />
                    <TextField
                        margin="normal"
                        required
                        fullWidth
                        name="password"
                        label="Пароль"
                        type="password"
                        id="password"
                        autoComplete="current-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                    />
                    {authStore.error && (
                        <Alert severity="error" sx={{ width: '100%', mt: 2 }}>
                            {authStore.error}
                        </Alert>
                    )}
                    <Button
                        type="submit"
                        fullWidth
                        variant="contained"
                        sx={{ mt: 3, mb: 2 }}
                        disabled={authStore.isLoading}
                    >
                        {authStore.isLoading ? <CircularProgress size={24} /> : 'Увійти'}
                    </Button>
                </Box>
            </Box>
        </Container>
    );
});

export default LoginPage;