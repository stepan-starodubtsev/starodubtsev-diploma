// src/components/offences/OffenceTable.jsx
import React from 'react';
import {
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
    IconButton, Tooltip, Box, Chip, TablePagination, Typography
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { format } from 'date-fns';
import { OffenceSeverityLabels, OffenceStatusLabels } from '../../constants'; // Для міток

const OffenceTable = ({
                          offences, onViewDetails,
                          page, rowsPerPage, count, onPageChange, onRowsPerPageChange
                      }) => {

    const getSeverityChipColor = (severityValue) => {
        switch (severityValue) {
            case 'low': return 'info';
            case 'medium': return 'warning';
            case 'high': return 'error';
            case 'critical': return 'error'; // Сильно червоний
            default: return 'default';
        }
    };

    const getStatusChipColor = (statusValue) => {
        switch (statusValue) {
            case 'new': return 'primary';
            case 'in_progress': return 'secondary';
            case 'closed_false_positive': return 'default';
            case 'closed_true_positive': return 'success';
            default: return 'default';
        }
    };

    // Пагінація на клієнті (якщо count - це загальна кількість з сервера, то ця логіка не потрібна)
    // const displayedOffences = offences.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

    return (
        <Box>
            <TableContainer component={Paper} elevation={2}>
                <Table sx={{ minWidth: 650 }} aria-label="offences table">
                    <TableHead sx={{ backgroundColor: (theme) => theme.palette.action.hover }}>
                        <TableRow>
                            <TableCell>ID</TableCell>
                            <TableCell sx={{minWidth: 300}}>Заголовок</TableCell>
                            <TableCell>Серйозність</TableCell>
                            <TableCell>Статус</TableCell>
                            <TableCell sx={{minWidth: 150}}>Час Виявлення</TableCell>
                            <TableCell>Правило ID</TableCell>
                            <TableCell align="center">Дії</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {/* Використовуємо `offences` напряму, якщо пагінація серверна */}
                        {offences.length > 0 ? offences.map((offence) => (
                            <TableRow key={offence.id} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                                <TableCell>{offence.id}</TableCell>
                                <TableCell component="th" scope="row">
                                    <Typography variant="body2" sx={{ wordBreak: 'break-word'}}>
                                        {offence.title}
                                    </Typography>
                                </TableCell>
                                <TableCell>
                                    <Chip
                                        label={(OffenceSeverityLabels.find(s => s.value === offence.severity)?.label || offence.severity || '').toUpperCase()}
                                        color={getSeverityChipColor(offence.severity)}
                                        size="small"
                                    />
                                </TableCell>
                                <TableCell>
                                    <Chip
                                        label={OffenceStatusLabels.find(s => s.value === offence.status)?.label || offence.status}
                                        color={getStatusChipColor(offence.status)}
                                        size="small"
                                        variant="outlined"
                                    />
                                </TableCell>
                                <TableCell>
                                    {offence.detected_at ? format(new Date(offence.detected_at), 'yyyy-MM-dd HH:mm:ss') : 'N/A'}
                                </TableCell>
                                <TableCell align="center">{offence.correlation_rule_id}</TableCell>
                                <TableCell align="center">
                                    <Tooltip title="Переглянути Деталі / Змінити Статус">
                                        <IconButton size="small" onClick={() => onViewDetails(offence)} color="primary">
                                            <VisibilityIcon />
                                        </IconButton>
                                    </Tooltip>
                                </TableCell>
                            </TableRow>
                        )) : (
                            <TableRow>
                                <TableCell colSpan={7} align="center">Немає даних про офенси</TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </TableContainer>
            <TablePagination
                rowsPerPageOptions={[5, 10, 25, 50]}
                component="div"
                count={count} // Має бути загальна кількість з сервера (offenceStore.totalOffences)
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={onPageChange}
                onRowsPerPageChange={onRowsPerPageChange}
                labelRowsPerPage="Рядків на сторінці:"
            />
        </Box>
    );
};

export default OffenceTable;