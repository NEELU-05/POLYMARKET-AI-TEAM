import { useState, useEffect } from "react";
import AnimatedNumber from "./AnimatedNumber";
import { Info } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string;
  color?: "green" | "red" | "yellow" | "default";
  sparklineData?: number[];
  tooltip?: string;
}

function getSparklinePath(data: number[], width: number, height: number): string {
  if (!data || data.length < 2) return "";
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const padding = 2;
  const w = width - padding * 2;
  const h = height - padding * 2;
  
  const stepX = w / (data.length - 1);
  return data.map((d, i) => {
    const x = padding + i * stepX;
    const y = padding + (h - ((d - min) / range) * h);
    return `${i === 0 ? "M" : "L"} ${x} ${y}`;
  }).join(" ");
}

export default function MetricCard({
  label,
  value,
  color = "default",
  sparklineData,
  tooltip,
}: MetricCardProps) {
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    setIsUpdating(true);
    const timer = setTimeout(() => setIsUpdating(false), 1200);
    return () => clearTimeout(timer);
  }, [value]);

  const colorClass = {
    green: "text-green-400",
    red: "text-red-400",
    yellow: "text-yellow-400",
    default: "text-white",
  }[color];

  const strokeColor = {
    green: "#22c55e",
    red: "#ef4444",
    yellow: "#eab308",
    default: "#3b82f6",
  }[color];

  // Try to parse number and format for AnimatedNumber
  let isNumber = false;
  let numValue = 0;
  let format: "integer" | "decimal" | "percentage" | "currency" = "integer";
  let symbol = "";

  const cleanValue = value.replace(/,/g, '');
  if (cleanValue.includes("%")) {
    const num = parseFloat(cleanValue.replace("%", ""));
    if (!isNaN(num)) {
      isNumber = true;
      numValue = num;
      format = "percentage";
    }
  } else if (cleanValue.includes("₹") || cleanValue.includes("$")) {
    const num = parseFloat(cleanValue.replace(/[₹$\+]/g, ""));
    if (!isNaN(num)) {
      isNumber = true;
      numValue = value.includes("-") ? -num : num;
      format = "currency";
      symbol = value.includes("₹") ? "₹" : "$";
    }
  } else {
    const num = parseFloat(cleanValue);
    if (!isNaN(num)) {
      isNumber = true;
      numValue = num;
      format = cleanValue.includes(".") ? "decimal" : "integer";
    }
  }

  return (
    <div className={`stat-card ${isUpdating ? "metric-updated" : ""}`}>
      <div className="flex items-center gap-1.5 group">
        <p className="text-xs text-slate-400">{label}</p>
        {tooltip && (
          <div className="relative flex items-center">
            <Info className="h-3 w-3 text-slate-500 cursor-help" />
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-slate-800 text-xs text-slate-200 border border-slate-700 rounded-md shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10 pointer-events-none">
              {tooltip}
              <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800"></div>
            </div>
          </div>
        )}
      </div>
      <div className="flex items-end justify-between mt-1">
        <p className={`text-xl font-bold ${colorClass} leading-none`}>
          {isNumber ? (
            <AnimatedNumber value={numValue} format={format} currencySymbol={symbol} />
          ) : (
            value
          )}
        </p>
        {sparklineData && sparklineData.length > 1 && (
          <svg width="60" height="20" className="opacity-70 shrink-0">
            <path
              d={getSparklinePath(sparklineData, 60, 20)}
              fill="none"
              stroke={strokeColor}
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </div>
    </div>
  );
}
