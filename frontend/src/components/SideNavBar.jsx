import React from 'react';
import { NavLink } from 'react-router-dom'; // Use NavLink for active styling
import { useAppContext } from '@/contexts/AppContext';
import { Badge } from "@/components/ui/badge";
import { LayoutDashboard, Users } from 'lucide-react'; // Import icons
import { cn } from "@/lib/utils"; // For conditional classes

// Enhanced NavLink component for Icon-Above-Text style
function SidebarNavLink({ to, icon: Icon, label, badgeCount }) {
  return (
    <NavLink
      to={to}
      // Use a function with NavLink to check active state
      className={({ isActive }) =>
        cn(
          "flex flex-col items-center justify-center p-3 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 relative space-y-1",
          isActive && "bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100 font-medium"
        )
      }
      // Ensure index route (/) also matches /access-logs for active state
      end={to !== "/access-logs"} 
    >
      <Icon className="h-6 w-6" />
      <span className="text-xs font-medium">{label}</span>
      {badgeCount > 0 && (
        <Badge variant="destructive" className="absolute top-1 right-1 px-1.5 py-0.5 text-xs">
          {/* Only show count if > 0, adjust positioning as needed */}
          {badgeCount}
        </Badge>
      )}
    </NavLink>
  );
}

function SideNavBar() {
  const { pendingCount } = useAppContext();

  const navContent = (
    // Use flex-col for icon-above-text layout
    <nav className="flex flex-col items-center space-y-3 pt-4">
      <SidebarNavLink to="/access-logs" icon={LayoutDashboard} label="Logs" badgeCount={pendingCount} />
      <SidebarNavLink to="/employees" icon={Users} label="Employees" />
      {/* Add more links here if needed, following the same pattern */}
    </nav>
  );

  return (
    // Always visible sidebar
    // Removed hidden md:flex classes, kept fixed width and flex styling
    <aside className="flex flex-col w-20 bg-white dark:bg-gray-800 shadow-md flex-shrink-0 items-center py-4 h-screen fixed left-0 top-0 z-40"> {/* Added h-screen, fixed, left-0, top-0, z-40 */}
      {/* Maybe add a logo/title placeholder here if desired */}
      <div className="flex-grow w-full px-2">
        {navContent}
      </div>
    </aside>
  );
}

export default SideNavBar; 