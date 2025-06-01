// src/components/correlation/CorrelationRuleTable.jsx
import React from 'react';
import {
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
    IconButton, Tooltip, Box, Chip, Switch, TablePagination
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
// import correlationStore from '../../stores/correlationStore'; // Для оновлення is_enabled

const CorrelationRuleTable = ({ rules, onEdit, onDelete /*, onToggleEnable */ }) => {
    const [page, setPage] = React.useState(0);
    const [rowsPerPage, setRowsPerPage] = React.useState(10);

    const handleChangePage = (event, newPage) => setPage(newPage);
    const handleChangeRowsPerPage = (event) => {
        setRowsPerPage(parseInt(event.target.value, 10));
        setPage(0);
    };
    const displayedRules = rules.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

    const getSeverityChipColor = (severityValue) => {
        switch (severityValue) {
            case 'low': return 'info';
            case 'medium': return 'warning';
            case 'high': return 'error';
            case 'critical': return 'error'; // Або інший колір для critical
            default: return 'default';
        }
    };

    return (
        <Box>
            <TableContainer component={Paper} elevation={2}>
                <Table sx={{ minWidth: 650 }} aria-label="correlation rules table">
                    <TableHead sx={{ backgroundColor: (theme) => theme.palette.action.hover }}>
                        <TableRow>
                            <TableCell>ID</TableCell>
                            <TableCell sx={{minWidth: 200}}>Назва</TableCell>
                            <TableCell>Тип Правила</TableCell>
                            <TableCell sx={{minWidth: 150}}>Поле Події</TableCell>
                            <TableCell>Тип IoC</TableCell>
                            <TableCell>Серйозність Офенса</TableCell>
                            <TableCell>Активне</TableCell>
                            <TableCell align="center">Дії</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {displayedRules.length > 0 ? displayedRules.map((rule) => (
                            <TableRow key={rule.id} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                                <TableCell>{rule.id}</TableCell>
                                <TableCell component="th" scope="row">{rule.name}</TableCell>
                                <TableCell>
                                    <Chip label={rule.rule_type?.value || rule.rule_type} size="small" variant="outlined"/>
                                </TableCell>
                                <TableCell>{rule.event_field_to_match?.value || rule.event_field_to_match || 'N/A'}</TableCell>
                                <TableCell>{rule.ioc_type_to_match?.value || rule.ioc_type_to_match || 'N/A'}</TableCell>
                                <TableCell>
                                    <Chip
                                        label={(rule.generated_offence_severity?.value || rule.generated_offence_severity || '').toUpperCase()}
                                        color={getSeverityChipColor(rule.generated_offence_severity?.value || rule.generated_offence_severity)}
                                        size="small"
                                    />
                                </TableCell>
                                <TableCell>
                                    <Switch
                                        checked={rule.is_enabled}
                                        // onChange={() => onToggleEnable(rule.id, !rule.is_enabled)} // Потрібно реалізувати
                                        size="small"
                                        color="success"
                                        // disabled // Поки не реалізовано оновлення
                                    />
                                </TableCell>
                                <TableCell align="center">
                                    <Tooltip title="Редагувати">
                                        <IconButton size="small" onClick={() => onEdit(rule)} color="primary">
                                            <EditIcon />
                                        </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Видалити">
                                        <IconButton size="small" onClick={() => onDelete(rule.id)} color="error">
                                            <DeleteIcon />
                                        </IconButton>
                                    </Tooltip>
                                </TableCell>
                            </TableRow>
                        )) : (
                            <TableRow>
                                <TableCell colSpan={8} align="center">Немає правил кореляції</TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </TableContainer>
            <TablePagination
                rowsPerPageOptions={[5, 10, 25]} component="div"
                count={rules.length} rowsPerPage={rowsPerPage} page={page}
                onPageChange={handleChangePage} onRowsPerPageChange={handleChangeRowsPerPage}
                labelRowsPerPage="Рядків на сторінці:"
            />
        </Box>
    );
};

export default CorrelationRuleTable;