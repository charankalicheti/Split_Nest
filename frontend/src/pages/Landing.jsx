import { Link } from "react-router-dom";

const previewPeople = [
  { initials: "C", name: "Charan", detail: "Paid ₹5,000", tone: "coral" },
  { initials: "G", name: "Gopi", detail: "Owes ₹1,000", tone: "lavender" },
  { initials: "P", name: "Pavan", detail: "All settled", tone: "mint" },
  { initials: "V", name: "Vinay", detail: "Gets back ₹1,000", tone: "gold" },
];

function Landing() {
  return (
    <main className="landing-page">
      <header className="landing-header">
        <Link className="landing-brand" to="/" aria-label="Splitnest home">
          <span className="landing-brand-mark">↔</span>
          <span>split<span>nest</span></span>
        </Link>
        <nav className="landing-nav" aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#features">Features</a>
        </nav>
        <Link className="landing-header-cta" to="/app">Open the app <span aria-hidden="true">→</span></Link>
      </header>

      <section className="landing-hero">
        <div className="landing-hero-copy">
          <div className="landing-kicker"><span /> SHARED EXPENSES, WITHOUT THE MATH</div>
          <h1>Good times together.<br /><span>Splits made simple.</span></h1>
          <p>Keep group expenses clear, know who owes whom, and settle up without the awkward calculations.</p>
          <div className="landing-hero-actions">
            <Link className="landing-primary-cta" to="/app">Start splitting expenses <span aria-hidden="true">→</span></Link>
            <a className="landing-secondary-cta" href="#how-it-works">See how it works</a>
          </div>
          <div className="landing-trust"><span className="landing-check">✓</span> No account needed <span className="landing-trust-dot">·</span> Free to use</div>
        </div>

        <div className="landing-preview-wrap" aria-label="Example group balance preview">
          <div className="landing-preview-glow" />
          <article className="landing-preview">
            <div className="landing-preview-top">
              <div>
                <span className="landing-preview-label">YOUR GROUP</span>
                <h2>Goa Trip <span aria-hidden="true">☀</span></h2>
              </div>
              <span className="landing-currency">INR⌄</span>
            </div>
            <div className="landing-preview-total">
              <span>Total shared expenses</span>
              <strong>₹20,000</strong>
              <div className="landing-preview-progress"><span /></div>
              <small>4 people sharing equally</small>
            </div>
            <div className="landing-preview-people">
              {previewPeople.map((person) => (
                <div className="landing-preview-person" key={person.name}>
                  <span className={`landing-person-avatar ${person.tone}`}>{person.initials}</span>
                  <span className="landing-preview-person-name">{person.name}</span>
                  <span className={`landing-preview-person-detail ${person.detail.startsWith("Owes") ? "owes" : person.detail.startsWith("Gets") ? "gets" : ""}`}>{person.detail}</span>
                </div>
              ))}
            </div>
            <div className="landing-settle-tip">
              <span className="landing-tip-icon">↗</span>
              <span><small>ONE SIMPLE SETTLEMENT</small><strong>Gopi pays Vinay</strong></span>
              <b>₹1,000</b>
            </div>
          </article>
          <div className="landing-floating-note"><span>✓</span> Balances, sorted</div>
        </div>
      </section>

      <section className="landing-proof" aria-label="App highlights">
        <span>MADE FOR REAL-LIFE SHARED PLANS</span>
        <div><strong>Weekend trips</strong><i /> <strong>Roommates</strong><i /> <strong>Dinners out</strong><i /> <strong>Everyday expenses</strong></div>
      </section>

      <section className="landing-features" id="features">
        <div className="landing-section-heading">
          <span className="landing-kicker">LESS TRACKING. MORE LIVING.</span>
          <h2>Everything your group needs.<br /><span>Nothing it doesn’t.</span></h2>
        </div>
        <div className="landing-feature-grid">
          <article className="landing-feature-card">
            <span className="landing-feature-icon purple">♧</span>
            <h3>One group, one place</h3>
            <p>Add people to a group and keep every shared expense together.</p>
          </article>
          <article className="landing-feature-card">
            <span className="landing-feature-icon coral">↗</span>
            <h3>Splits that make sense</h3>
            <p>Split evenly or enter each person’s share. Balances update for you.</p>
          </article>
          <article className="landing-feature-card">
            <span className="landing-feature-icon green">✓</span>
            <h3>Know who pays whom</h3>
            <p>See clear settlement suggestions, so everyone knows exactly what to do.</p>
          </article>
        </div>
      </section>

      <section className="landing-how" id="how-it-works">
        <div className="landing-how-copy">
          <span className="landing-kicker">UP AND RUNNING IN A MINUTE</span>
          <h2>From “I’ll get you later”<br />to <span>all settled.</span></h2>
          <p>Create a group, add your people, then record expenses as you go. Splitnest keeps the running total and works out the simplest way to settle.</p>
          <Link className="landing-primary-cta" to="/app">Create your first group <span aria-hidden="true">→</span></Link>
        </div>
        <ol className="landing-steps">
          <li><span>01</span><div><strong>Create a group</strong><p>Name your trip, home, or shared plan.</p></div></li>
          <li><span>02</span><div><strong>Add people and expenses</strong><p>Choose who paid and how to split the cost.</p></div></li>
          <li><span>03</span><div><strong>Settle up simply</strong><p>Follow clear payment suggestions. Done.</p></div></li>
        </ol>
      </section>

      <section className="landing-bottom-cta">
        <div><span className="landing-kicker">YOUR NEXT GROUP PLAN STARTS HERE</span><h2>Make sharing the easy part.</h2><p>Get your group on the same page before the next bill arrives.</p></div>
        <Link className="landing-primary-cta" to="/app">Open Splitnest <span aria-hidden="true">→</span></Link>
      </section>

      <footer className="landing-footer">
        <Link className="landing-brand" to="/" aria-label="Splitnest home">
          <span className="landing-brand-mark">↔</span>
          <span>split<span>nest</span></span>
        </Link>
        <span>Shared moments, made a little simpler.</span>
        <Link to="/app">Go to your groups →</Link>
      </footer>
    </main>
  );
}

export default Landing;
