import api from "./api";

export async function getGroups() {
  const { data } = await api.get("/groups");
  return data;
}

export async function getGroup(groupId) {
  const { data } = await api.get(`/groups/${groupId}`);
  return data;
}

export async function createGroup(payload) {
  const { data } = await api.post("/groups", payload);
  return data;
}

export async function addGroupMember(groupId, name) {
  const { data } = await api.post(`/groups/${groupId}/members`, { name });
  return data;
}

export async function deleteGroup(groupId) {
  await api.delete(`/groups/${groupId}`);
}