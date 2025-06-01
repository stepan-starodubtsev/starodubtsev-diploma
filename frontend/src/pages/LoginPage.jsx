// src/pages/LoginPage.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Container, Box, TextField, Button, Typography, Paper, Avatar
} from '@mui/material';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';

// Припустимо, що setIsAuthenticated передається як prop з App.js
const LoginPage = ({ setIsAuthenticated }) => {
    const navigate = useNavigate();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = (event) => {
        event.preventDefault();
        // Імітація логіну: просто перевіряємо, чи поля не порожні
        if (username.trim() && password.trim()) {
            setError('');
            console.log('Login successful (mocked)');
            // Тут ти б викликав authStore.login(username, password)
            // А зараз просто встановлюємо стан "автентифікований"
            if (setIsAuthenticated) {
                setIsAuthenticated(true);
            }
            navigate('/'); // Перенаправлення на головну сторінку
        } else {
            setError('Будь ласка, введіть ім\'я користувача та пароль.');
        }
    };

    return (
        <Container component="main" maxWidth="xs">
            <Paper elevation={6} sx={{ marginTop: 8, display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 4 }}>
                <Avatar sx={{ m: 1, bgcolor: 'secondary.main' }}>
                    <LockOutlinedIcon />
                </Avatar>
                <Typography component="h1" variant="h5">
                    Вхід до системи
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
                        error={!!error && !username.trim()} // Показувати помилку, якщо поле порожнє і є загальна помилка
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
                        error={!!error && !password.trim()} // Показувати помилку, якщо поле порожнє і є загальна помилка
                    />
                    {error && (
                        <Typography color="error" variant="body2" sx={{ mt: 1 }}>
                            {error}
                        </Typography>
                    )}
                    <Button
                        type="submit"
                        fullWidth
                        variant="contained"
                        sx={{ mt: 3, mb: 2 }}
                    >
                        Увійти
                    </Button>
                </Box>
            </Paper>
        </Container>
    );
};

export default LoginPage;