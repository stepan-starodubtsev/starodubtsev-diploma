// src/components/response/ResponsePipelineTable.jsx
import React from 'react';
import {
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
    IconButton, Tooltip, Box, Chip, Switch, TablePagination, Typography
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { format } from 'date-fns';

const ResponsePipelineTable = ({
                                   pipelines,
                                   onEdit,
                                   onDelete,
                                   onToggleEnable,
                                   // Пагінація
                                   page,
                                   rowsPerPage,
                                   count,
                                   onPageChange,
                                   onRowsPerPageChange
                               }) => {

    return (
        <Box>
            <TableContainer component={Paper} elevation={2}>
                <Table sx={{ minWidth: 650 }} aria-label="response pipelines table">
                    <TableHead sx={{ backgroundColor: (theme) => theme.palette.action.hover }}>
                        <TableRow>
                            <TableCell>ID</TableCell>
                            <TableCell sx={{ minWidth: 250 }}>Назва Пайплайна</TableCell>
                            <TableCell>ID Правила-Тригера</TableCell>
                            <TableCell>К-ть Дій</TableCell>
                            <TableCell>Активний</TableCell>
                            <TableCell align="center">Дії</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {pipelines.length > 0 ? pipelines.map((pipeline) => (
                            <TableRow key={pipeline.id} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                                <TableCell>{pipeline.id}</TableCell>
                                <TableCell component="th" scope="row">{pipeline.name}</TableCell>
                                <TableCell>{pipeline.trigger_correlation_rule_id || 'N/A'}</TableCell>
                                <TableCell align="center">{pipeline.actions_config?.length || 0}</TableCell>
                                <TableCell>
                                    <Switch
                                        checked={pipeline.is_enabled}
                                        onChange={(e) => onToggleEnable(pipeline.id, e.target.checked)}
                                        size="small"
                                        color="success"
                                    />
                                </TableCell>
                                <TableCell align="center">
                                    <Tooltip title="Редагувати Пайплайн">
                                        <IconButton size="small" onClick={() => onEdit(pipeline)} color="primary">
                                            <EditIcon />
                                        </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Видалити Пайплайн">
                                        <IconButton size="small" onClick={() => onDelete(pipeline.id)} color="error">
                                            <DeleteIcon />
                                        </IconButton>
                                    </Tooltip>
                                </TableCell>
                            </TableRow>
                        )) : (
                            <TableRow>
                                <TableCell colSpan={6} align="center">Немає визначених пайплайнів реагування</TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </TableContainer>
            <TablePagination
                rowsPerPageOptions={[5, 10, 25]}
                component="div"
                count={count}
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={onPageChange}
                onRowsPerPageChange={onRowsPerPageChange}
                labelRowsPerPage="Рядків на сторінці:"
            />
        </Box>
    );
};

export default ResponsePipelineTable;