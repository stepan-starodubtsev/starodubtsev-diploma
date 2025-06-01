// src/components/dashboard/AptOffencesWidget.jsx
import React, { useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { Typography, Paper, Box, CircularProgress, Alert } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import correlationStore from '../../stores/correlationStore';
// import aptGroupStore from '../../stores/aptGroupStore'; // Якщо імена APT потрібні звідси

const AptOffencesWidget = observer(() => {
    useEffect(() => {
        correlationStore.fetchOffencesByApt(7); // За останні 7 днів
        // aptGroupStore.fetchAptGroups(); // Якщо потрібно для мапінгу ID на імена, хоча API вже повертає ім'я
    }, []);

    const { offencesByApt, isLoadingOffencesByApt, error } = correlationStore;

    if (isLoadingOffencesByApt) {
        return <Box display="flex" justifyContent="center" py={2}><CircularProgress size={24} /></Box>;
    }

    if (error && offencesByApt.length === 0) {
        return <Alert severity="error" sx={{ mt: 1 }}>{String(error)}</Alert>;
    }

    // Дані для графіка (мають містити apt_name та offence_count)
    const chartData = offencesByApt.map(item => ({
        name: item.apt_name || `APT ID: ${item.apt_id}`, // Використовуємо apt_name, якщо є
        Кількість: item.offence_count
    }));


    return (
        <Paper elevation={2} sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
                Офенси за APT-Угрупованнями
            </Typography>
            {chartData.length === 0 && !isLoadingOffencesByApt ? (
                <Typography variant="body2">Дані про офенси по APT відсутні за обраний період.</Typography>
            ) : (
                <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 45 }}> {/* Зменшено лівий відступ, збільшено нижній */}
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" angle={-35} textAnchor="end" interval={0} style={{ fontSize: '0.8rem' }} />
                        <YAxis allowDecimals={false} />
                        <Tooltip />
                        <Legend wrapperStyle={{ fontSize: '0.9rem' }} />
                        <Bar dataKey="Кількість" fill="#82ca9d" barSize={30} />
                    </BarChart>
                </ResponsiveContainer>
            )}
        </Paper>
    );
});

export default AptOffencesWidget;