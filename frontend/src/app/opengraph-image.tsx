import { ImageResponse } from "next/og";

export const runtime = "edge";

export const size = {
  width: 1200,
  height: 630,
};

export const contentType = "image/png";

export default function Image(): ImageResponse {
  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          width: "100%",
          height: "100%",
          padding: "56px",
          background:
            "linear-gradient(135deg, #fffaf8 0%, #fff3f6 52%, #f2edff 100%)",
          color: "#25212a",
          fontFamily:
            'Inter, "Helvetica Neue", "Segoe UI", Arial, sans-serif',
        }}
      >
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            borderRadius: "40px",
            border: "1px solid rgba(235, 228, 238, 0.9)",
            background: "rgba(255, 255, 255, 0.84)",
            padding: "48px",
            boxShadow: "0 24px 60px rgba(96, 63, 88, 0.12)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <div
              style={{
                display: "flex",
                width: "72px",
                height: "72px",
                alignItems: "center",
                justifyContent: "center",
                borderRadius: "20px",
                background: "linear-gradient(135deg, #f36f8f, #8d7be8)",
                color: "#ffffff",
                fontSize: "30px",
                fontWeight: 800,
              }}
            >
              CA
            </div>
            <div style={{ display: "flex", flexDirection: "column" }}>
              <div style={{ fontSize: "28px", fontWeight: 800 }}>ClueAI</div>
              <div style={{ fontSize: "18px", color: "#6f6877" }}>
                SKU review operating system
              </div>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
            <div
              style={{
                fontSize: "64px",
                fontWeight: 800,
                lineHeight: 1.04,
                letterSpacing: "-0.04em",
                maxWidth: "760px",
              }}
            >
              Review signals that turn into action and follow-up validation.
            </div>
            <div
              style={{
                fontSize: "28px",
                lineHeight: 1.45,
                color: "#6f6877",
                maxWidth: "760px",
              }}
            >
              Built for cross-border sellers who need to know what to fix first,
              who owns it, and whether the next batch of reviews says the change
              worked.
            </div>
          </div>

          <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
            {["Review analysis", "Action Center", "Follow-up tracking"].map(
              (label) => (
                <div
                  key={label}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "14px 20px",
                    borderRadius: "999px",
                    border: "1px solid rgba(235, 228, 238, 0.95)",
                    background: "#ffffff",
                    fontSize: "22px",
                    fontWeight: 700,
                  }}
                >
                  {label}
                </div>
              ),
            )}
          </div>
        </div>

        <div
          style={{
            width: "340px",
            marginLeft: "32px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            gap: "20px",
          }}
        >
          <div
            style={{
              borderRadius: "28px",
              border: "1px solid rgba(235, 228, 238, 0.9)",
              background: "rgba(255,255,255,0.8)",
              padding: "24px",
            }}
          >
            <div style={{ fontSize: "18px", color: "#6f6877" }}>
              High-risk SKU
            </div>
            <div style={{ marginTop: "10px", fontSize: "36px", fontWeight: 800 }}>
              12
            </div>
          </div>
          <div
            style={{
              borderRadius: "28px",
              border: "1px solid rgba(235, 228, 238, 0.9)",
              background: "rgba(255,255,255,0.8)",
              padding: "24px",
            }}
          >
            <div style={{ fontSize: "18px", color: "#6f6877" }}>
              Action Center handoff
            </div>
            <div style={{ marginTop: "10px", fontSize: "36px", fontWeight: 800 }}>
              08
            </div>
          </div>
          <div
            style={{
              borderRadius: "28px",
              border: "1px solid rgba(235, 228, 238, 0.9)",
              background: "rgba(255,255,255,0.8)",
              padding: "24px",
            }}
          >
            <div style={{ fontSize: "18px", color: "#6f6877" }}>
              Follow-up validation
            </div>
            <div style={{ marginTop: "10px", fontSize: "36px", fontWeight: 800 }}>
              23%
            </div>
          </div>
        </div>
      </div>
    ),
    {
      ...size,
    },
  );
}
