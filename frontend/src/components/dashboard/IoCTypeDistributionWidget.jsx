// src/components/dashboard/IoCTypeDistributionWidget.jsx
import React from 'react';
import { Typography, Paper, Box } from '@mui/material';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'; // Приклад з Recharts

const IoCTypeDistributionWidget = ({ iocs }) => {
    const typeCounts = iocs.reduce((acc, ioc) => {
        const type = ioc.type?.value || ioc.type || 'unknown';
        acc[type] = (acc[type] || 0) + 1;
        return acc;
    }, {});

    const dataForChart = Object.entries(typeCounts).map(([name, value]) => ({ name, value }));

    const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AA00FF', '#FF00AA'];

    return (
        <Box>
            <Typography variant="h6" gutterBottom>Розподіл Активних IoC за Типом</Typography>
            {dataForChart.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                        <Pie
                            data={dataForChart}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                            outerRadius={80}
                            fill="#8884d8"
                            dataKey="value"
                        >
                            {dataForChart.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                        </Pie>
                        <Tooltip />
                        <Legend />
                    </PieChart>
                </ResponsiveContainer>
            ) : (
                <Typography variant="body2">Немає даних для відображення.</Typography>
            )}
        </Box>
    );
};

export default IoCTypeDistributionWidget;