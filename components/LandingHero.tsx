
"use client";

import Image from "next/image";

export default function LandingHero() {
  return (
    <div className="landing-hero">
      {/* HEADER */}
      <header
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "96px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 4.5%",
          borderBottom: "1px solid rgba(255,255,255,0.09)",
        }}
      >
        {/* GALASEE LOGO */}
        <div className="galasee-brand">
          <Image
            src="/logo.png"
            alt="GALASEE Logo"
            width={400}
            height={150}
            priority
            className="galasee-logo"
          />
        </div>

        <span
          style={{
            color: "#8095a5",
            fontSize: "11px",
            letterSpacing: "2px",
          }}
        >
          NASA SPACE APPS CHALLENGE 2026
        </span>
      </header>

      {/* MAIN CONTENT */}
      <section
        style={{
          position: "absolute",
          top: "22%",
          left: "6.5%",
          width: "43%",
          maxWidth: "650px",
        }}
      >
        <p
          style={{
            color: "#6bd4db",
            fontSize: "12px",
            letterSpacing: "3px",
            fontWeight: 500,
            marginBottom: "32px",
          }}
        >
          NASA SPACE APPS CHALLENGE 2026
        </p>

        <h1
          style={{
            fontSize: "clamp(52px, 5.8vw, 100px)",
            fontWeight: 300,
            letterSpacing: "-4px",
            lineHeight: 1.05,
            margin: 0,
            color: "#e8eef5",
          }}
        >
          TIDEAWARE
          <span style={{ color: "#65cbd2" }}>.</span>
        </h1>

        <p
          style={{
            marginTop: "32px",
            color: "#91a7b6",
            fontSize: "12px",
            letterSpacing: "2.5px",
          }}
        >
          CHALLENGE / DANCING WITH THE SARS
        </p>

        <div
          style={{
            width: "58px",
            height: "1px",
            background: "#64d2da",
            marginTop: "40px",
            marginBottom: "40px",
          }}
        />

        <h2
          style={{
            fontSize: "22px",
            fontWeight: 400,
            color: "#f1f5f9",
            marginBottom: "22px",
          }}
        >
          Not every change is what it seems.
        </h2>

        <p
          style={{
            color: "#91a7b6",
            fontSize: "14px",
            lineHeight: 1.9,
            maxWidth: "470px",
          }}
        >
          An interactive Earth observation platform using
          satellite radar to detect coastal changes and
          distinguish tidal variations from potential
          environmental threats.
        </p>

        <div
          style={{
            marginTop: "48px",
            display: "flex",
            alignItems: "center",
            gap: "14px",
            color: "#67dce3",
            fontSize: "12px",
            letterSpacing: "2px",
          }}
        >
          <span style={{ fontSize: "24px" }}>◎</span>
          CLICK THE EARTH TO EXPLORE
          <span>↗</span>
        </div>
      </section>

      {/* EARTH LABEL */}
      <div
        style={{
          position: "absolute",
          right: "6%",
          bottom: "17%",
          color: "#8299a9",
          fontSize: "11px",
          letterSpacing: "2px",
          lineHeight: 2,
        }}
      >
        EARTH OBSERVATION
        <div>NASA–ISRO / NISAR</div>
      </div>

      {/* FOOTER */}
      <footer
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          minHeight: "80px",
          padding: "0 4.5%",
          borderTop: "1px solid rgba(255,255,255,0.09)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          color: "#8194a5",
          fontSize: "11px",
          letterSpacing: "1.5px",
        }}
      >
        <span>GALASEE © 2026</span>

        <span>DUONG · TRANG · NGOC</span>

        <span
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
          }}
        >
          <span
            style={{
              width: "7px",
              height: "7px",
              borderRadius: "50%",
              background: "#62d7d9",
              boxShadow: "0 0 12px #62d7d9",
            }}
          />
          SYSTEM ONLINE
        </span>
      </footer>
    </div>
  );
}
