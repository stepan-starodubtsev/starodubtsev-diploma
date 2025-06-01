// src/components/apt_groups/APTGroupTable.jsx
import React from 'react';
import {
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
    IconButton, Tooltip, Box, Chip, TablePagination, Link as MuiLink
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility'; // Для перегляду IoC
import { format } from 'date-fns';

const APTGroupTable = ({ aptGroups, onEdit, onDelete, onViewIoCs }) => {
    const [page, setPage] = React.useState(0);
    const [rowsPerPage, setRowsPerPage] = React.useState(10);

    const handleChangePage = (event, newPage) => setPage(newPage);
    const handleChangeRowsPerPage = (event) => {
        setRowsPerPage(parseInt(event.target.value, 10));
        setPage(0);
    };

    const displayedGroups = aptGroups.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

    return (
        <Box>
            <TableContainer component={Paper} elevation={2}>
                <Table sx={{ minWidth: 650 }} aria-label="apt groups table">
                    <TableHead sx={{ backgroundColor: (theme) => theme.palette.action.hover }}>
                        <TableRow>
                            <TableCell>ID</TableCell>
                            <TableCell>Назва</TableCell>
                            <TableCell>Псевдоніми</TableCell>
                            <TableCell>Мотивація</TableCell>
                            <TableCell>Складність</TableCell>
                            <TableCell>Країна</TableCell>
                            <TableCell align="center">Дії</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {displayedGroups.length > 0 ? displayedGroups.map((group) => (
                            <TableRow key={group.id} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                                <TableCell>{group.id}</TableCell>
                                <TableCell component="th" scope="row">{group.name}</TableCell>
                                <TableCell>{(group.aliases || []).join(', ')}</TableCell>
                                <TableCell>{group.primary_motivation?.value || group.primary_motivation || 'N/A'}</TableCell>
                                <TableCell>{group.sophistication?.value || group.sophistication || 'N/A'}</TableCell>
                                <TableCell>{group.country_of_origin || 'N/A'}</TableCell>
                                <TableCell align="center">
                                    <Tooltip title="Переглянути пов'язані IoC">
                                        <IconButton size="small" onClick={() => onViewIoCs(group.id)} color="info">
                                            <VisibilityIcon />
                                        </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Редагувати">
                                        <IconButton size="small" onClick={() => onEdit(group)} color="primary">
                                            <EditIcon />
                                        </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Видалити">
                                        <IconButton size="small" onClick={() => onDelete(group.id)} color="error">
                                            <DeleteIcon />
                                        </IconButton>
                                    </Tooltip>
                                </TableCell>
                            </TableRow>
                        )) : (
                            <TableRow>
                                <TableCell colSpan={7} align="center">Немає даних про APT угруповання</TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </TableContainer>
            <TablePagination
                rowsPerPageOptions={[5, 10, 25]}
                component="div"
                count={aptGroups.length}
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={handleChangePage}
                onRowsPerPageChange={handleChangeRowsPerPage}
                labelRowsPerPage="Рядків на сторінці:"
            />
        </Box>
    );
};

export default APTGroupTable;