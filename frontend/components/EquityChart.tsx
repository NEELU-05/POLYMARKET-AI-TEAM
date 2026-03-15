"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { EquityPoint } from "@/services/api";

interface EquityChartProps {
  data: EquityPoint[];
  currency: string;
}

export default function EquityChart({ data, currency }: EquityChartProps) {
  const formatted = data.map((d) => ({
    ...d,
    time: new Date(d.timestamp).toLocaleDateString("en-IN", {
      month: "short",
      day: "numeric",
    }),
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={formatted}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis dataKey="time" stroke="#64748b" fontSize={12} />
        <YAxis stroke="#64748b" fontSize={12} />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1e293b",
            border: "1px solid #334155",
            borderRadius: "8px",
            color: "#f1f5f9",
          }}
          formatter={(value: string | number) => [
            `${currency}${Number(value).toFixed(2)}`,
            "Balance",
          ]}
        />
        <ReferenceLine y={500} stroke="#3b82f6" strokeDasharray="3 3" />
        <ReferenceLine y={350} stroke="#eab308" strokeDasharray="3 3" />
        <ReferenceLine y={300} stroke="#ef4444" strokeDasharray="3 3" />
        <Line
          type="monotone"
          dataKey="balance"
          stroke="#22c55e"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
