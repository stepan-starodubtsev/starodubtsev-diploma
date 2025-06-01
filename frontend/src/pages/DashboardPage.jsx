// src/pages/DashboardPage.jsx
import React from 'react';
import { Box, Typography, Paper } from '@mui/material'; // Використовуємо MUI компоненти

const DashboardPage = () => {
    return (
        <Box>
            <Typography variant="h4" gutterBottom>
                Головна Панель (Дашборд)
            </Typography>
            <Paper elevation={3} sx={{ padding: 2, marginTop: 2 }}>
                <Typography variant="body1">
                    Тут буде відображатися основна інформація та статистика системи.
                </Typography>
                {/* Додай сюди компоненти для дашборду */}
            </Paper>
        </Box>
    );
};

export default DashboardPage;