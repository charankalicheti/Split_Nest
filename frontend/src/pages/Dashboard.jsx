import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createExpense,
  deleteExpense,
  getGroupBalances,
  getGroupExpenses,
  getGroupSettlementSuggestions,
  updateExpense,
} from "../services/expenseApi";
import { getApiErrorMessage } from "../services/api";
import {
  addGroupMember,
  createGroup,
  deleteGroup,
  getGroup,
  getGroups,
} from "../services/groupApi";
import { SUPPORTED_CURRENCIES, formatCurrency } from "../utils/formatCurrency";

const EMPTY_GROUPS = [];

function Dashboard() {
  const [groups, setGroups] = useState(EMPTY_GROUPS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [query, setQuery] = useState("");
  const [chartGroupId, setChartGroupId] = useState("");
  const [dialog, setDialog] = useState("");
  const [dialogError, setDialogError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [editingExpenseId, setEditingExpenseId] = useState(null);
  const [groupForm, setGroupForm] = useState({
    name: "",
    description: "",
    currency: "USD",
    member_names: ["Me"],
  });
  const [memberForm, setMemberForm] = useState({ group_id: "", name: "" });
  const [expenseForm, setExpenseForm] = useState({
    group_id: "",
    paid_by: "",
    description: "",
    amount: "",
    split_type: "equal",
    splits: [],
  });

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const userGroups = await getGroups();
      const details = await Promise.all(userGroups.map(async (group) => {
        const [detail, expenses, balances, settlementSuggestions] = await Promise.all([
          getGroup(group.id),
          getGroupExpenses(group.id),
          getGroupBalances(group.id),
          getGroupSettlementSuggestions(group.id),
        ]);
        return {
          ...group,
          members: detail.members,
          expenses,
          balances,
          settlements: settlementSuggestions.suggestions,
        };
      }));
      setGroups(details);
      setChartGroupId((selected) =>
        details.some((group) => String(group.id) === String(selected))
          ? selected
          : details.length
            ? String(details[0].id)
            : "",
      );
      setExpenseForm((current) => ({
        ...current,
        group_id: details.some((group) => String(group.id) === current.group_id)
          ? current.group_id
          : details.length ? String(details[0].id) : "",
        paid_by: (() => {
          const selectedGroup = details.find(
            (group) => String(group.id) === current.group_id,
          ) || details[0];
          return selectedGroup?.members.some(
            (member) => String(member.id) === String(current.paid_by),
          )
            ? current.paid_by
            : selectedGroup?.members[0]?.id?.toString() || "";
        })(),
      }));
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard, reloadKey]);

  const activeGroup = groups.find((group) => String(group.id) === String(chartGroupId));
  const activeExpenses = useMemo(() => {
    if (!activeGroup) return [];
    return activeGroup.expenses
      .map((expense) => ({
        ...expense,
        payer_name: activeGroup.members.find((member) => member.id === expense.paid_by)?.name
          || "A participant",
      }))
      .filter((expense) =>
        `${expense.description} ${expense.payer_name}`
          .toLowerCase()
          .includes(query.toLowerCase()),
      );
  }, [activeGroup, query]);
  const totalSpend = activeGroup?.expenses.reduce(
    (sum, expense) => sum + Number(expense.amount),
    0,
  ) || 0;
  const spentByMember = useMemo(() => {
    const totals = new Map();
    activeGroup?.expenses.forEach((expense) => {
      totals.set(
        expense.paid_by,
        (totals.get(expense.paid_by) || 0) + Number(expense.amount),
      );
    });
    return totals;
  }, [activeGroup]);
  const totalReceivable = activeGroup?.balances.members.reduce(
    (sum, member) => sum + Math.max(0, Number(member.net_balance)),
    0,
  ) || 0;

  async function submitGroup(event) {
    event.preventDefault();
    setDialogError("");
    const memberNames = groupForm.member_names.map((name) => name.trim());
    if (memberNames.some((name) => !name)) {
      setDialogError("Enter a name for each participant or remove the empty field.");
      return;
    }

    setSubmitting(true);
    try {
      await createGroup({
        name: groupForm.name.trim(),
        description: groupForm.description.trim() || null,
        currency: groupForm.currency,
        member_names: memberNames,
      });
      setDialog("");
      setGroupForm({ name: "", description: "", currency: "USD", member_names: ["Me"] });
      setReloadKey((key) => key + 1);
    } catch (requestError) {
      setDialogError(getApiErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  async function submitExpense(event) {
    event.preventDefault();
    setDialogError("");
    setSubmitting(true);
    try {
      const payload = {
        description: expenseForm.description.trim(),
        amount: expenseForm.amount,
        paid_by: Number(expenseForm.paid_by),
        split_type: expenseForm.split_type,
        ...(expenseForm.split_type === "custom" && {
          splits: expenseForm.splits.map((split) => ({
            member_id: Number(split.member_id),
            amount: split.amount,
          })),
        }),
      };
      if (editingExpenseId) {
        await updateExpense(editingExpenseId, payload);
      } else {
        await createExpense(Number(expenseForm.group_id), payload);
      }
      setDialog("");
      setEditingExpenseId(null);
      setExpenseForm((current) => ({
        ...current,
        description: "",
        amount: "",
        split_type: "equal",
        splits: [],
      }));
      setReloadKey((key) => key + 1);
    } catch (requestError) {
      setDialogError(getApiErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  function openExpenseEditor(expense) {
    setExpenseForm({
      group_id: String(expense.group_id),
      paid_by: String(expense.paid_by),
      description: expense.description,
      amount: String(expense.amount),
      split_type: expense.split_type,
      splits: expense.splits.map((split) => ({
        member_id: split.member_id,
        amount: String(split.amount),
      })),
    });
    setEditingExpenseId(expense.id);
    setDialogError("");
    setDialog("expense");
  }

  async function handleDeleteExpense(expense) {
    const confirmed = window.confirm(
      `Delete "${expense.description}"? This will update the group balances.`,
    );
    if (!confirmed) return;

    setError("");
    try {
      await deleteExpense(expense.id);
      setReloadKey((key) => key + 1);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    }
  }

  async function submitMember(event) {
    event.preventDefault();
    setDialogError("");
    setSubmitting(true);
    try {
      await addGroupMember(Number(memberForm.group_id), memberForm.name.trim());
      setDialog("");
      setMemberForm((current) => ({ ...current, name: "" }));
      setReloadKey((key) => key + 1);
    } catch (requestError) {
      setDialogError(getApiErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteGroup(group) {
    const confirmed = window.confirm(
      `Delete "${group.name}" and all its expenses and settlements? This cannot be undone.`,
    );
    if (!confirmed) return;

    setError("");
    try {
      await deleteGroup(group.id);
      setReloadKey((key) => key + 1);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    }
  }

  return (
    <div className="app-shell reference-app">
      <main className="reference-main" id="overview">
        <header className="reference-breadcrumb">
          <div className="reference-crumbs">
            <span>My groups</span>
            <span aria-hidden="true">/</span>
            {groups.length ? (
              <select
                aria-label="Select group"
                value={chartGroupId}
                onChange={(event) => setChartGroupId(event.target.value)}
              >
                {groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
              </select>
            ) : <strong>Groups</strong>}
          </div>
          <div className="reference-header-actions">
            {activeGroup && <div className="reference-currency"><span>Currency</span><strong>{activeGroup.currency}</strong></div>}
            <button className="button button-secondary" type="button" onClick={() => { setDialogError(""); setDialog("group"); }}>＋ New group</button>
          </div>
        </header>

        <div className="reference-content">
          {error && <div className="dashboard-error" role="alert"><span>{error}</span><button type="button" onClick={() => setReloadKey((key) => key + 1)}>Try again</button></div>}

          {loading && !activeGroup ? (
            <div className="reference-empty">Loading your groups…</div>
          ) : !activeGroup ? (
            <section className="reference-empty-state">
              <h1>Start a group to split expenses</h1>
              <p>Create a group, add the people sharing expenses, and track who owes whom.</p>
              <button className="button button-primary" type="button" onClick={() => { setDialogError(""); setDialog("group"); }}>＋ Create your first group</button>
            </section>
          ) : <>
            <section className="reference-title-row">
              <div>
                <p className="reference-eyebrow">SHARED EXPENSES</p>
                <h1>{activeGroup.name}</h1>
                <p className="reference-subtitle">{activeGroup.description || "Shared expenses, simply split."}</p>
              </div>
              <button className="reference-delete-button" type="button" onClick={() => handleDeleteGroup(activeGroup)}>Delete group</button>
            </section>

            <section className="reference-summary" aria-label={`${activeGroup.name} summary`}>
              <article className="reference-stat">
                <span className="reference-stat-icon spend">↗</span>
                <div><span className="reference-stat-label">Total spent</span><strong>{loading ? "…" : formatCurrency(totalSpend, activeGroup.currency)}</strong></div>
              </article>
              <article className="reference-stat">
                <span className="reference-stat-icon people">♧</span>
                <div><span className="reference-stat-label">Members</span><strong>{activeGroup.members.length}</strong></div>
              </article>
              <article className="reference-stat">
                <span className="reference-stat-icon transactions">▤</span>
                <div><span className="reference-stat-label">Transactions</span><strong>{activeGroup.expenses.length}</strong></div>
              </article>
              <article className="reference-stat">
                <span className="reference-stat-icon balance">↓</span>
                <div><span className="reference-stat-label">To receive</span><strong className="reference-stat-positive">{formatCurrency(totalReceivable, activeGroup.currency)}</strong></div>
              </article>
            </section>

            <section className="reference-columns">
              <article className="reference-panel expense-panel" id="transactions">
                <div className="reference-panel-heading">
                  <h2>Recent expenses</h2>
                  <div className="reference-panel-actions">
                    <label className="reference-search"><span aria-hidden="true">⌕</span><input aria-label="Search expenses" placeholder="Search expenses…" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
                    <button className="button button-primary" type="button" onClick={() => { setExpenseForm((current) => ({ ...current, group_id: String(activeGroup.id), paid_by: activeGroup.members[0]?.id?.toString() || "", description: "", amount: "", split_type: "equal", splits: [] })); setEditingExpenseId(null); setDialogError(""); setDialog("expense"); }}>＋ Add expense</button>
                  </div>
                </div>
                <div className="reference-table-scroll">
                  <table className="reference-expense-table">
                    <thead><tr><th>Date</th><th>Description</th><th>Paid by</th><th>Amount</th><th>Split</th><th><span className="visually-hidden">Actions</span></th></tr></thead>
                    <tbody>
                      {loading && <tr><td colSpan="6" className="reference-table-empty">Loading expenses…</td></tr>}
                      {!loading && !activeExpenses.length && <tr><td colSpan="6" className="reference-table-empty">{query ? "No expenses match your search." : "No expenses yet. Add one to get started."}</td></tr>}
                      {!loading && activeExpenses.slice(0, 12).map((expense) => {
                        const firstSplit = expense.splits[0];
                        return <tr key={expense.id}>
                          <td>{new Date(expense.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</td>
                          <td className="reference-expense-description">{expense.description}</td>
                          <td><span className="reference-payer"><span className="reference-avatar small">{expense.payer_name.slice(0, 1).toUpperCase()}</span>{expense.payer_name}</span></td>
                          <td className="reference-money">{formatCurrency(Number(expense.amount), activeGroup.currency)}</td>
                          <td><span className="reference-split">{expense.split_type === "equal" && firstSplit ? `${formatCurrency(Number(firstSplit.amount), activeGroup.currency)} each` : "Custom split"}</span></td>
                          <td className="reference-expense-actions">
                            <button type="button" onClick={() => openExpenseEditor(expense)}>Edit</button>
                            <button type="button" onClick={() => handleDeleteExpense(expense)}>Delete</button>
                          </td>
                        </tr>;
                      })}
                    </tbody>
                  </table>
                </div>
                {activeExpenses.length > 12 && <p className="reference-table-foot">Showing 12 of {activeExpenses.length} expenses</p>}
              </article>

              <article className="reference-panel members-panel" id="groups">
                <div className="reference-panel-heading">
                  <div><h2>Group members</h2><p>Trip spend paid by each person</p></div>
                  <button className="reference-inline-button" type="button" onClick={() => { setMemberForm({ group_id: String(activeGroup.id), name: "" }); setDialogError(""); setDialog("member"); }}>＋ Add person</button>
                </div>
                <div className="reference-member-list">
                  {activeGroup.members.map((member, index) => {
                    return <div className="reference-member" key={member.id}>
                      <span className={`reference-avatar avatar-${index % 4}`}>{member.name.slice(0, 1).toUpperCase()}</span>
                      <strong>{member.name}</strong>
                      <div className="reference-member-financials">
                        <span className="reference-member-spent">
                          <small>trip spend</small>
                          <b>{formatCurrency(spentByMember.get(member.id) || 0, activeGroup.currency)}</b>
                        </span>
                      </div>
                    </div>;
                  })}
                  {!activeGroup.members.length && <div className="reference-table-empty">Add a person to this group.</div>}
                </div>
              </article>
            </section>

            <section className="reference-panel reference-balances" id="balances">
              <div className="reference-panel-heading">
                <div><h2>Balances</h2><p>Each person’s share after expenses.</p></div>
              </div>
              <div className="reference-balance-grid">
                {activeGroup.balances.members.map((member, index) => {
                  const balance = Number(member.net_balance) || 0;
                  return <article className="reference-balance-card" key={member.member_id}>
                    <span className={`reference-avatar avatar-${index % 4}`}>{member.name.slice(0, 1).toUpperCase()}</span>
                    <div><strong>{member.name}</strong><small className={balance > 0 ? "positive" : balance < 0 ? "negative" : ""}>{balance > 0 ? "gets back" : balance < 0 ? "owes" : "settled"}</small></div>
                    <strong className={`reference-balance-value ${balance > 0 ? "positive" : balance < 0 ? "negative" : ""}`}>{formatCurrency(Math.abs(balance), activeGroup.currency)}</strong>
                  </article>;
                })}
              </div>
              <div className="reference-settlement-list">
                <h3>Suggested payments</h3>
                {activeGroup.settlements.length
                  ? activeGroup.settlements.map((settlement) => {
                    const payer = activeGroup.members.find((member) => member.id === settlement.payer_id);
                    const payee = activeGroup.members.find((member) => member.id === settlement.payee_id);
                    return <div className="reference-settlement" key={`${settlement.payer_id}-${settlement.payee_id}`}>
                      <span><strong>{payer?.name}</strong><span> pays </span><strong>{payee?.name}</strong></span>
                      <b>{formatCurrency(Number(settlement.amount), activeGroup.currency)}</b>
                    </div>;
                  })
                  : <p className="reference-all-settled">Everyone is settled up.</p>}
              </div>
            </section>
          </>}

          <footer className="reference-footer"><span>Splitnest · Shared expenses made simple</span><button type="button" onClick={() => { setDialogError(""); setDialog("group"); }}>＋ Create group</button></footer>
        </div>
      </main>

      {dialog && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setDialog(""); }}>
        <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
          <div className="dialog-heading"><span className="dialog-icon">{dialog === "group" || dialog === "member" ? "♧" : "↗"}</span><button className="icon-button subtle" type="button" aria-label="Close dialog" onClick={() => setDialog("")}>×</button></div>
          <h2 id="dialog-title">{dialog === "group" ? "Create a group" : dialog === "member" ? "Add a participant" : editingExpenseId ? "Edit expense" : "Add an expense"}</h2>
          <p className="dialog-subtitle">{dialog === "group" ? "Add the people who will share expenses." : dialog === "member" ? "Add someone to an existing group." : editingExpenseId ? "Update the description, payer, or amount." : "Record a real expense in one of your groups."}</p>
          {dialog === "group" ? <form className="dialog-form" onSubmit={submitGroup}>
            <label>Group name<input autoFocus required maxLength="100" value={groupForm.name} onChange={(event) => setGroupForm({ ...groupForm, name: event.target.value })} placeholder="e.g. Housemates" /></label>
            <label>Description <span className="optional-label">Optional</span><input maxLength="500" value={groupForm.description} onChange={(event) => setGroupForm({ ...groupForm, description: event.target.value })} placeholder="What is this group for?" /></label>
            <div className="participant-fields">
              <div className="participant-fields-heading">
                <span>Participants</span>
                <span className="optional-label">Add everyone sharing expenses</span>
              </div>
              {groupForm.member_names.map((name, index) => (
                <div className="participant-input-row" key={index}>
                  <input
                    aria-label={`Participant ${index + 1} name`}
                    required
                    maxLength="100"
                    value={name}
                    onChange={(event) => setGroupForm({
                      ...groupForm,
                      member_names: groupForm.member_names.map((memberName, memberIndex) =>
                        memberIndex === index ? event.target.value : memberName,
                      ),
                    })}
                    placeholder={`Person ${index + 1}`}
                  />
                  {groupForm.member_names.length > 1 && (
                    <button
                      className="remove-participant-button"
                      type="button"
                      aria-label={`Remove participant ${index + 1}`}
                      onClick={() => setGroupForm({
                        ...groupForm,
                        member_names: groupForm.member_names.filter((_, memberIndex) => memberIndex !== index),
                      })}
                    >×</button>
                  )}
                </div>
              ))}
              <button
                className="add-participant-button"
                type="button"
                disabled={groupForm.member_names.length >= 100}
                onClick={() => setGroupForm({
                  ...groupForm,
                  member_names: [...groupForm.member_names, ""],
                })}
              >＋ Add person</button>
            </div>
            <label>Group currency<select value={groupForm.currency} onChange={(event) => setGroupForm({ ...groupForm, currency: event.target.value })}>{SUPPORTED_CURRENCIES.map((currency) => <option key={currency.code} value={currency.code}>{currency.code} — {currency.name}</option>)}</select></label>
            {dialogError && <p className="form-error" role="alert">{dialogError}</p>}
            <button className="button button-primary dialog-submit" type="submit" disabled={submitting}>{submitting ? "Creating…" : "Create group"}</button>
          </form> : dialog === "expense" ? <form className="dialog-form" onSubmit={submitExpense}>
            <label>Group<select required disabled={Boolean(editingExpenseId)} value={expenseForm.group_id} onChange={(event) => {
              const selectedGroup = groups.find((group) => String(group.id) === event.target.value);
              setExpenseForm({
                ...expenseForm,
                group_id: event.target.value,
                paid_by: selectedGroup?.members[0]?.id?.toString() || "",
                splits: expenseForm.split_type === "custom"
                  ? selectedGroup?.members.map((member) => ({ member_id: member.id, amount: "" })) || []
                  : [],
              });
            }}>{groups.map((group) => <option key={group.id} value={group.id}>{group.name} ({group.currency})</option>)}</select></label>
            <label>Paid by<select required value={expenseForm.paid_by} onChange={(event) => setExpenseForm({ ...expenseForm, paid_by: event.target.value })}>
              {groups.find((group) => String(group.id) === expenseForm.group_id)?.members.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
            </select></label>
            <label>What was it for?<input autoFocus required maxLength="255" value={expenseForm.description} onChange={(event) => setExpenseForm({ ...expenseForm, description: event.target.value })} placeholder="e.g. Groceries" /></label>
            <label>Amount<div className="amount-input"><span>{groups.find((group) => String(group.id) === expenseForm.group_id)?.currency || ""}</span><input required type="number" min="0.01" step="0.01" value={expenseForm.amount} onChange={(event) => setExpenseForm({ ...expenseForm, amount: event.target.value })} placeholder="0.00" /></div></label>
            <label>Split<select value={expenseForm.split_type} onChange={(event) => {
              const splitType = event.target.value;
              const selectedGroup = groups.find((group) => String(group.id) === expenseForm.group_id);
              setExpenseForm({
                ...expenseForm,
                split_type: splitType,
                splits: splitType === "custom"
                  ? selectedGroup?.members.map((member) => ({ member_id: member.id, amount: "" })) || []
                  : [],
              });
            }}><option value="equal">Split equally</option><option value="custom">Custom amounts</option></select></label>
            {expenseForm.split_type === "custom" ? <div className="expense-split-fields">
              <span className="optional-label">Enter each participant’s share. Shares must add up to the expense total.</span>
              {expenseForm.splits.map((split, index) => {
                const selectedMemberIds = expenseForm.splits.map((item) => Number(item.member_id));
                return <div className="expense-split-row" key={`${split.member_id}-${index}`}>
                  <select
                    aria-label={`Participant ${index + 1} for custom split`}
                    required
                    value={split.member_id}
                    onChange={(event) => setExpenseForm({
                      ...expenseForm,
                      splits: expenseForm.splits.map((item, splitIndex) =>
                        splitIndex === index ? { ...item, member_id: Number(event.target.value) } : item,
                      ),
                    })}
                  >
                    {groups.find((group) => String(group.id) === expenseForm.group_id)?.members
                      .filter((member) => Number(member.id) === Number(split.member_id)
                        || !selectedMemberIds.includes(Number(member.id)))
                      .map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
                  </select>
                  <input
                    aria-label={`Share amount for participant ${index + 1}`}
                    required
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={split.amount}
                    onChange={(event) => setExpenseForm({
                      ...expenseForm,
                      splits: expenseForm.splits.map((item, splitIndex) =>
                        splitIndex === index ? { ...item, amount: event.target.value } : item,
                      ),
                    })}
                    placeholder="0.00"
                  />
                  {expenseForm.splits.length > 1 && <button
                    className="remove-expense-split"
                    type="button"
                    aria-label={`Remove custom split participant ${index + 1}`}
                    onClick={() => setExpenseForm({
                      ...expenseForm,
                      splits: expenseForm.splits.filter((_, splitIndex) => splitIndex !== index),
                    })}
                  >×</button>}
                </div>;
              })}
              {expenseForm.splits.length < groups.find((group) => String(group.id) === expenseForm.group_id)?.members.length
                && <button className="add-participant-button" type="button" onClick={() => {
                  const selectedGroup = groups.find((group) => String(group.id) === expenseForm.group_id);
                  const nextMember = selectedGroup?.members.find((member) =>
                    !expenseForm.splits.some((split) => Number(split.member_id) === member.id),
                  );
                  if (nextMember) setExpenseForm({
                    ...expenseForm,
                    splits: [...expenseForm.splits, { member_id: nextMember.id, amount: "" }],
                  });
                }}>＋ Add participant to split</button>}
            </div> : <p className="split-help">This expense will be split equally between all participants.</p>}
            {dialogError && <p className="form-error" role="alert">{dialogError}</p>}
            <button className="button button-primary dialog-submit" type="submit" disabled={submitting || !groups.length}>{submitting ? "Saving…" : editingExpenseId ? "Save changes" : "Save expense"}</button>
          </form> : <form className="dialog-form" onSubmit={submitMember}>
            <label>Group<select required value={memberForm.group_id} onChange={(event) => setMemberForm({ ...memberForm, group_id: event.target.value })}>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
            <label>Participant name<input autoFocus required maxLength="100" value={memberForm.name} onChange={(event) => setMemberForm({ ...memberForm, name: event.target.value })} placeholder="e.g. Alex" /></label>
            {dialogError && <p className="form-error" role="alert">{dialogError}</p>}
            <button className="button button-primary dialog-submit" type="submit" disabled={submitting || !groups.length}>{submitting ? "Adding…" : "Add participant"}</button>
          </form>}
          <p className="dialog-note">Groups and expenses are saved for anyone using this app.</p>
        </section>
      </div>}
    </div>
  );
}

export default Dashboard;
