import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-teal-200/80 bg-teal-50 text-[#0F766E] shadow-2xs",
        secondary:
          "border-slate-200 bg-slate-100 text-[#172033]",
        destructive:
          "border-rose-200 bg-rose-50 text-rose-800 shadow-2xs",
        outline: "border-[#E2E8F0] bg-white text-[#172033]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
