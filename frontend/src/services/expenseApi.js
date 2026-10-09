import api from "./api";

export async function getGroupExpenses(groupId) {
  const { data } = await api.get(`/expenses/groups/${groupId}`);
  return data;
}

export async function createExpense(groupId, payload) {
  const { data } = await api.post(`/expenses/groups/${groupId}`, payload);
  return data;
}

export async function updateExpense(expenseId, payload) {
  const { data } = await api.put(`/expenses/${expenseId}`, payload);
  return data;
}

export async function deleteExpense(expenseId) {
  await api.delete(`/expenses/${expenseId}`);
}

export async function getGroupBalances(groupId) {
  const { data } = await api.get(`/groups/${groupId}/balances`);
  return data;
}

export async function getGroupSettlementSuggestions(groupId) {
  const { data } = await api.get(`/groups/${groupId}/balances/suggestions`);
  return data;
}