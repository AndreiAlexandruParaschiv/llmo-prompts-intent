import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, 
  FolderKanban, 
  MessageSquareText, 
  Globe, 
  Lightbulb,
  Unlink,
  Swords,
  ChevronLeft,
  ChevronRight,
  Menu,
} from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useProjectStore } from '@/stores/projectStore'

const navigation = [
  { name: 'Projects', href: '/projects', icon: FolderKanban },
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Pages', href: '/pages', icon: Globe },
  { name: 'Prompts', href: '/prompts', icon: MessageSquareText },
  { name: 'Opportunities', href: '/opportunities', icon: Lightbulb },
  { name: 'Unmatched Content', href: '/orphan-pages', icon: Unlink },
  { name: 'Competitive Analysis', href: '/competitive', icon: Swords },
]

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()
  const { selectedProjectId } = useProjectStore()

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-slate-950">
      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside 
        className={cn(
          "fixed lg:static inset-y-0 left-0 z-50 flex flex-col",
          "bg-gradient-to-b from-slate-900 via-slate-900 to-slate-800",
          "border-r border-slate-700/50 shadow-2xl shadow-slate-900/50",
          "transition-all duration-300 ease-in-out",
          collapsed ? "w-16" : "w-64",
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Logo */}
        <div className="flex items-center h-16 px-4 border-b border-slate-700/50">
          <div className={cn(
            "flex items-center gap-3 overflow-hidden",
            collapsed && "lg:justify-center"
          )}>
            <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/30">
              <Lightbulb className="w-5 h-5 text-white" />
            </div>
            {!collapsed && (
              <div className="flex flex-col">
                <span className="font-bold text-white text-sm tracking-tight">
                  LLMO Prompt Analyzer
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const isActive = location.pathname.startsWith(item.href)
            return (
              <NavLink
                key={item.name}
                to={item.href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg",
                  "transition-all duration-200",
                  "group relative",
                  isActive 
                    ? "bg-gradient-to-r from-cyan-500/20 to-blue-500/10 text-cyan-400 shadow-lg shadow-cyan-500/10" 
                    : "text-slate-400 hover:text-white hover:bg-slate-800/50",
                  collapsed && "lg:justify-center lg:px-2"
                )}
              >
                <item.icon className={cn(
                  "w-5 h-5 flex-shrink-0 transition-transform duration-200",
                  isActive ? "text-cyan-400" : "group-hover:scale-110"
                )} />
                {!collapsed && (
                  <span className="font-medium text-sm truncate">{item.name}</span>
                )}
                {isActive && (
                  <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-gradient-to-b from-cyan-400 to-blue-500 rounded-l-full" />
                )}
                {/* Tooltip for collapsed state */}
                {collapsed && (
                  <div className="hidden lg:group-hover:block absolute left-full ml-2 px-2 py-1 bg-slate-800 text-white text-sm rounded-md whitespace-nowrap z-50 shadow-lg">
                    {item.name}
                  </div>
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* Current Project indicator */}
        {selectedProjectId && !collapsed && (
          <div className="mx-3 mb-3 p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">
              Active Project
            </div>
            <div className="text-sm text-white font-medium truncate">
              {selectedProjectId.slice(0, 8)}...
            </div>
          </div>
        )}

        {/* Collapse button */}
        <div className="hidden lg:flex p-3 border-t border-slate-700/50">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setCollapsed(!collapsed)}
            className={cn(
              "w-full text-slate-400 hover:text-white hover:bg-slate-800",
              collapsed && "px-2"
            )}
          >
            {collapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <>
                <ChevronLeft className="w-4 h-4 mr-2" />
                <span>Collapse</span>
              </>
            )}
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center px-4 lg:px-6 gap-4">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="w-5 h-5" />
          </Button>

          <div className="flex-1">
            <h1 className="text-lg font-semibold text-slate-900 dark:text-white">
              {navigation.find(n => location.pathname.startsWith(n.href))?.name || 'Dashboard'}
            </h1>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

