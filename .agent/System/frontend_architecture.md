# Frontend Architecture

## Related Documentation
- [README.md](../README.md) - Documentation index
- [Project Architecture](project_architecture.md) - Overall system architecture

---

## 1. Overview

The frontend is a Next.js application providing a web interface for conversation import, AI-powered project draft generation, and real-time chat.

### Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 15.5.4 | React framework with App Router |
| React | 19.1.0 | UI library |
| TypeScript | 5.x | Type-safe JavaScript |
| Tailwind CSS | 4.x | Utility-first CSS (PostCSS plugin) |
| shadcn/ui | - | Component library (new-york style) |
| Zustand | - | Feature-level state management |
| React Query | - | Server state management |
| react-hook-form | - | Form state management |
| Zod | 4.x | Schema validation |
| Lucide React | - | Icon library |

### Key Capabilities
- Import conversations from ChatGPT, Claude, and Grok share URLs
- AI-powered project draft generation with version history
- Real-time streaming chat with multiple LLM providers
- Vector-based semantic search across conversations
- File attachments with model capability filtering

---

## 2. Feature-Based Architecture

### Folder Structure

The project follows a **feature-based architecture**. The `app/` directory contains routes only, while business logic is organized into features:

```
frontend/
├── app/                    # Next.js App Router (routes only)
│   ├── layout.tsx
│   ├── globals.css
│   ├── login/
│   └── (dashboard)/
│
├── features/               # Feature-based organization
│   ├── auth/              # Authentication feature
│   ├── conversations/     # Conversation management
│   ├── project-drafts/    # Project draft generation
│   ├── search/            # Search functionality
│   └── dashboard/         # Main dashboard
│
├── shared/                 # Shared across multiple features
│   ├── components/        # Shared UI components
│   ├── hooks/             # Shared hooks
│   ├── types/             # Shared types
│   └── utils/             # Shared utilities
│
├── lib/                    # External service integrations & utilities
│   ├── utils.ts           # Utility functions (cn, etc.)
│   ├── config.ts          # Environment configuration
│   └── api-client.ts      # API client setup
│
├── providers/              # Context providers
│   └── auth-provider.tsx
│
├── clients/                # API clients
│   └── backend-client.ts
│
├── components/             # shadcn/ui components (auto-generated)
│   └── ui/
│
└── public/                 # Static assets
```

### Feature Structure Template

Each feature should follow this consistent structure:

```
features/[feature]/
├── components/             # Feature-specific components
│   ├── ui/                # Feature-specific UI components
│   └── forms/             # Feature-specific forms
├── hooks/                  # React Query hooks for data operations
├── stores/                 # Zustand stores (if needed)
├── types/                  # Feature-specific types (or use entity files)
├── utils/                  # Feature-specific utilities
├── repositories/           # Data access layer
└── constants.ts            # Feature-specific constants
```

**Important**: Prefer entity files over separate `types/` folders. Types should be co-located with their domain entities.

---

## 3. Naming Conventions

### Files & Folders
- **Format**: `kebab-case`
- **Examples**:
  - `project-draft/`
  - `use-conversations.ts`
  - `conversation-card.tsx`
  - `api-adapters.ts`

### Hooks
- **Format**: `use-[hook-name].ts`
- **Examples**:
  - `use-auth.ts`
  - `use-search.ts`
  - `use-project-draft.ts`

### Types
- **Format**: `[feature-name].types.ts`
- **Examples**:
  - `conversation.types.ts`
  - `project-draft.types.ts`

### Import Examples

```typescript
// shadcn/ui components
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

// Feature imports
import { useConversations } from "@/features/conversations/hooks/use-conversations"
import { ConversationCard } from "@/features/conversations/components/conversation-card"

// Shared imports
import { cn } from "@/lib/utils"
import { useAuth } from "@/features/auth/hooks/use-auth"
```

---

## 4. UI & Styling

### Component Library

**shadcn/ui** configured with:
- **Style**: "new-york"
- **Base color**: "neutral"
- **Icon library**: `lucide-react`
- **CSS variables**: enabled

### Styling Approach

- **Framework**: Tailwind CSS v4 (PostCSS plugin)
- **Global styles**: `app/globals.css`
- **Utility function**: Use `cn()` from `@/lib/utils` for conditional classes

### Component Example

```typescript
import { cn } from "@/lib/utils"

interface MyComponentProps {
  className?: string
  children: React.ReactNode
}

export function MyComponent({ className, children }: MyComponentProps) {
  return (
    <div className={cn("rounded-lg border p-4", className)}>
      {children}
    </div>
  )
}
```

---

## 5. State Management

### Local Component State
- Use React's `useState` and `useReducer`
- For simple, component-scoped state

### Feature-Level State
- Use **Zustand** stores in `features/[feature]/stores/`
- **Important**: Do NOT create convenience hooks - use the store directly

```typescript
// features/dashboard/stores/dashboard-store.ts
import { create } from "zustand"

interface DashboardState {
  sidebarCollapsed: boolean
  toggleSidebar: () => void
}

export const useDashboardStore = create<DashboardState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
}))

// Usage - access store directly, no wrapper hook
const { sidebarCollapsed, toggleSidebar } = useDashboardStore()
```

### Server State
- Use **React Query** hooks in `features/[feature]/hooks/`
- Follow the `use-[type-name].ts` naming pattern

```typescript
// features/conversations/hooks/use-conversations.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"

export function useConversations() {
  return useQuery({
    queryKey: ["conversations"],
    queryFn: fetchConversations,
  })
}

export function useDeleteConversation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: deleteConversation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] })
    },
  })
}
```

---

## 6. Forms & Validation

### Form Management
- **Library**: `react-hook-form` for form state management
- **Validation**: Zod schemas with `@hookform/resolvers/zod`
- **UI Components**: shadcn/ui `Form` components
- **Location**: Place forms in `features/[feature]/components/forms/`

### Zod Schema Conventions
- Use `z.enum()` instead of deprecated `z.nativeEnum()`
- Define schemas in entity files or co-located with forms
- Export schemas for reuse in API routes and components

### Form Pattern (shadcn/ui)

```typescript
// features/projects/components/forms/create-project-form.tsx
"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { Button } from "@/components/ui/button"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"

const createProjectSchema = z.object({
  name: z.string().min(1, { message: "Name is required" }),
  description: z.string().optional(),
  status: z.enum(["active", "inactive"]),
})

type CreateProjectForm = z.infer<typeof createProjectSchema>

export function CreateProjectForm() {
  const form = useForm<CreateProjectForm>({
    resolver: zodResolver(createProjectSchema),
    defaultValues: {
      name: "",
      description: "",
      status: "active",
    },
  })

  function onSubmit(data: CreateProjectForm) {
    console.log(data)
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Project Name</FormLabel>
              <FormControl>
                <Input placeholder="My Project" {...field} />
              </FormControl>
              <FormDescription>
                The public display name for your project.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Input placeholder="Optional description" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" disabled={form.formState.isSubmitting}>
          Create Project
        </Button>
      </form>
    </Form>
  )
}
```

### Form Guidelines
1. Always add `"use client"` directive at the top of form files
2. Use shadcn/ui `Form` components (`FormField`, `FormItem`, `FormLabel`, `FormControl`, `FormMessage`)
3. Use `render` prop pattern with `FormField` for each input
4. Keep form schemas co-located with the form component
5. Use `z.infer<typeof schema>` for type inference
6. Handle loading states with `form.formState.isSubmitting`
7. Use consistent field naming with database schema
8. `FormMessage` automatically displays validation errors
9. Use `FormDescription` for helpful field hints

---

## 7. Development Guidelines

### When Creating New Features

1. Create feature folder in `features/`
2. Follow the feature structure template
3. Use kebab-case for all files and folders
4. Define types in entity files, not separate `types/` folders
5. Create repositories for data access
6. Use React Query hooks for server state
7. Use Zustand stores for complex local state

### Component Development

1. Start with shadcn/ui components when possible
2. Create feature-specific components in `features/[feature]/components/`
3. Create shared components in `shared/components/`
4. Use the `cn()` utility for conditional classes
5. Co-locate styles with components using Tailwind

### Adding a New Page

1. Create file in `app/` following App Router conventions
2. Use `"use client"` directive for client components
3. Import feature components, don't put logic in page files
4. Keep pages thin - they should compose feature components

---

## 8. Migration Guide

### When to Migrate

Identify code that needs migration when you see:

| Pattern | Issue | Target |
|---------|-------|--------|
| `components/FeatureName/` | Components grouped by feature in wrong location | `features/[feature]/components/` |
| `contexts/SomeContext.tsx` | React Context for feature state | Zustand store in `features/[feature]/stores/` |
| `hooks/useSomething.ts` | Global hooks folder | `features/[feature]/hooks/` or `shared/hooks/` |
| `useFeatureName.ts` (camelCase) | Wrong naming convention | `use-feature-name.ts` (kebab-case) |
| `types/feature.ts` | Separate types folder | Co-locate with entity or `[feature].types.ts` |
| Custom form handling | Not using shadcn/ui Form | Migrate to react-hook-form + shadcn/ui |

### Migration Steps

#### 1. Moving Components to Features

```bash
# Before
components/
├── ProjectDraft/
│   ├── ProjectDraft.tsx
│   ├── hooks/useProjectDraftState.ts
│   └── components/ProjectDraftHeader.tsx

# After
features/project-drafts/
├── components/
│   ├── project-draft.tsx
│   ├── project-draft-header.tsx
│   └── forms/
├── hooks/
│   └── use-project-draft-state.ts
└── types/
    └── project-draft.types.ts
```

Steps:
1. Create feature folder: `features/project-drafts/`
2. Move components, renaming to kebab-case
3. Move hooks to `features/project-drafts/hooks/`
4. Update all imports throughout the codebase
5. Delete old component folder

#### 2. Converting Context to Zustand

```typescript
// Before: contexts/DashboardContext.tsx
const DashboardContext = createContext<DashboardContextValue>(...)

export function DashboardProvider({ children }) {
  const [conversations, setConversations] = useState([])
  // ...
}

// After: features/dashboard/stores/dashboard-store.ts
import { create } from "zustand"

export const useDashboardStore = create((set) => ({
  conversations: [],
  setConversations: (conversations) => set({ conversations }),
  // ...
}))
```

Steps:
1. Create store in `features/[feature]/stores/`
2. Move state and actions to Zustand store
3. Replace `useContext(DashboardContext)` with `useDashboardStore()`
4. Remove Provider wrapper from layout
5. Delete old context file

#### 3. Renaming Hooks to Kebab-Case

```bash
# Before
hooks/useAuth.ts
hooks/useSearch.ts

# After
features/auth/hooks/use-auth.ts
features/search/hooks/use-search.ts
# OR if truly shared:
shared/hooks/use-auth.ts
```

#### 4. Migrating Forms to shadcn/ui

```typescript
// Before: Custom form handling
function MyForm() {
  const [name, setName] = useState("")
  const [error, setError] = useState("")

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!name) setError("Required")
    // ...
  }

  return (
    <form onSubmit={handleSubmit}>
      <input value={name} onChange={(e) => setName(e.target.value)} />
      {error && <span>{error}</span>}
    </form>
  )
}

// After: shadcn/ui Form with Zod
const schema = z.object({ name: z.string().min(1, "Required") })

function MyForm() {
  const form = useForm({ resolver: zodResolver(schema) })

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <FormField name="name" render={...} />
      </form>
    </Form>
  )
}
```

### Migration Priority

1. **High Priority** (do immediately):
   - New features should always follow the new architecture
   - Fix naming conventions when touching a file

2. **Medium Priority** (when working in the area):
   - Migrate components to features when modifying them
   - Convert contexts to Zustand when adding new state

3. **Low Priority** (dedicated refactoring):
   - Bulk rename files to kebab-case
   - Migrate all forms to shadcn/ui pattern

---

## 9. Configuration Files

| File | Purpose |
|------|---------|
| `next.config.ts` | Next.js configuration, image optimization |
| `tsconfig.json` | TypeScript configuration with path aliases |
| `components.json` | shadcn/ui configuration |
| `postcss.config.mjs` | PostCSS/Tailwind configuration |
| `.prettierrc` | Code formatting rules |
| `.eslintrc.js` | Linting rules |

### TypeScript Path Aliases

```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### Environment Variables

```bash
# .env.local
NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
NEXT_PUBLIC_ENVIRONMENT="development"
NEXT_PUBLIC_GOOGLE_CLIENT_ID="..."
```

---

## 10. Scripts

```bash
npm run dev          # Start dev server with Turbopack
npm run build        # Production build
npm run lint         # Run ESLint
npm run format       # Run Prettier
```
