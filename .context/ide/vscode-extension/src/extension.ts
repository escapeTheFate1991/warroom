import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

interface ContextResult {
    query: string;
    context_sources: any[];
    relevant_files: any[];
    patterns: any[];
    suggestions: string[];
}

interface SessionContext {
    session_id: string;
    current_task: string;
    started_at: string;
    last_activity: string;
    files_modified: string[];
    error_count: number;
    context_quality: number;
}

class WarRoomContextProvider implements vscode.TreeDataProvider<ContextItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<ContextItem | undefined | null | void> = new vscode.EventEmitter<ContextItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<ContextItem | undefined | null | void> = this._onDidChangeTreeData.event;

    private currentSession: SessionContext | null = null;
    private recentContexts: ContextResult[] = [];

    constructor(private context: vscode.ExtensionContext) {}

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: ContextItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: ContextItem): Thenable<ContextItem[]> {
        if (!element) {
            return Promise.resolve(this.getRootItems());
        }
        
        return Promise.resolve(element.children || []);
    }

    private getRootItems(): ContextItem[] {
        const items: ContextItem[] = [];

        // Current session
        if (this.currentSession) {
            items.push(new ContextItem(
                `Session: ${this.currentSession.current_task}`,
                `Quality: ${(this.currentSession.context_quality * 100).toFixed(0)}% | Errors: ${this.currentSession.error_count}`,
                vscode.TreeItemCollapsibleState.Collapsed,
                [
                    new ContextItem(`Task: ${this.currentSession.current_task}`, '', vscode.TreeItemCollapsibleState.None),
                    new ContextItem(`Started: ${new Date(this.currentSession.started_at).toLocaleString()}`, '', vscode.TreeItemCollapsibleState.None),
                    new ContextItem(`Files Modified: ${this.currentSession.files_modified.length}`, '', vscode.TreeItemCollapsibleState.None)
                ]
            ));
        } else {
            items.push(new ContextItem(
                'No Active Session',
                'Start a new development session',
                vscode.TreeItemCollapsibleState.None
            ));
        }

        // Recent contexts
        if (this.recentContexts.length > 0) {
            const contextItems = this.recentContexts.slice(0, 5).map(ctx => 
                new ContextItem(
                    `Context: ${ctx.query}`,
                    `${ctx.context_sources.length} sources, ${ctx.suggestions.length} suggestions`,
                    vscode.TreeItemCollapsibleState.None
                )
            );
            
            items.push(new ContextItem(
                'Recent Contexts',
                '',
                vscode.TreeItemCollapsibleState.Collapsed,
                contextItems
            ));
        }

        return items;
    }

    updateSession(session: SessionContext | null) {
        this.currentSession = session;
        this.refresh();
    }

    addContext(context: ContextResult) {
        this.recentContexts.unshift(context);
        if (this.recentContexts.length > 10) {
            this.recentContexts = this.recentContexts.slice(0, 10);
        }
        this.refresh();
    }
}

class ContextItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly description: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly children?: ContextItem[]
    ) {
        super(label, collapsibleState);
        this.tooltip = `${this.label}: ${this.description}`;
        this.description = description;
    }
}

export function activate(context: vscode.ExtensionContext) {
    console.log('War Room Context extension activated');

    const provider = new WarRoomContextProvider(context);
    vscode.window.registerTreeDataProvider('warRoomContext', provider);

    // Find project root
    const projectRoot = findProjectRoot();
    if (!projectRoot) {
        vscode.window.showWarningMessage('War Room context system not found in workspace');
        return;
    }

    // Load initial session
    loadCurrentSession(provider, projectRoot);

    // Commands
    const loadContextCommand = vscode.commands.registerCommand('warRoomContext.loadContext', async () => {
        const query = await vscode.window.showInputBox({
            prompt: 'Enter context query (error message, code pattern, etc.)',
            placeHolder: 'e.g., "JWT authentication failed"'
        });

        if (query) {
            const result = await loadContext(projectRoot, query);
            if (result) {
                provider.addContext(result);
                showContextResult(result);
            }
        }
    });

    const searchCodeCommand = vscode.commands.registerCommand('warRoomContext.searchCode', async () => {
        const query = await vscode.window.showInputBox({
            prompt: 'Enter semantic code search query',
            placeHolder: 'e.g., "user authentication flow"'
        });

        if (query) {
            const result = await searchCode(projectRoot, query);
            if (result) {
                showSearchResults(result);
            }
        }
    });

    const startSessionCommand = vscode.commands.registerCommand('warRoomContext.startSession', async () => {
        const task = await vscode.window.showInputBox({
            prompt: 'Enter development task description',
            placeHolder: 'e.g., "Fix authentication bug in user login"'
        });

        if (task) {
            const session = await startSession(projectRoot, task);
            if (session) {
                provider.updateSession(session);
                vscode.window.showInformationMessage(`Started session: ${session.session_id}`);
            }
        }
    });

    const showSessionCommand = vscode.commands.registerCommand('warRoomContext.showSession', async () => {
        const session = await getCurrentSession(projectRoot);
        if (session) {
            provider.updateSession(session);
            showSessionDetails(session);
        } else {
            vscode.window.showInformationMessage('No active development session');
        }
    });

    const trackErrorCommand = vscode.commands.registerCommand('warRoomContext.trackError', async () => {
        const editor = vscode.window.activeTextEditor;
        let selectedText = '';
        
        if (editor && editor.selection) {
            selectedText = editor.document.getText(editor.selection);
        }

        const errorMessage = await vscode.window.showInputBox({
            prompt: 'Enter error message',
            value: selectedText,
            placeHolder: 'Error message or description'
        });

        if (errorMessage) {
            const errorType = await vscode.window.showQuickPick([
                'authentication',
                'database', 
                'import',
                'typescript',
                'docker',
                'generic'
            ], {
                prompt: 'Select error type'
            });

            if (errorType) {
                await trackError(projectRoot, errorMessage, errorType);
                vscode.window.showInformationMessage('Error tracked in session');
            }
        }
    });

    // Auto-load context on file open
    const onDidOpenTextDocument = vscode.workspace.onDidOpenTextDocument(async (document) => {
        const config = vscode.workspace.getConfiguration('warRoomContext');
        if (!config.get('autoLoadContext')) {
            return;
        }

        const fileName = path.basename(document.fileName);
        
        // Auto-load context for certain file types
        if (fileName.includes('error') || fileName.includes('bug') || fileName.includes('fix')) {
            const context = await loadContext(projectRoot, `file: ${fileName}`);
            if (context && context.suggestions.length > 0) {
                const action = await vscode.window.showInformationMessage(
                    `Context suggestions available for ${fileName}`,
                    'Show Suggestions'
                );
                
                if (action === 'Show Suggestions') {
                    showContextResult(context);
                }
            }
        }
    });

    // Track file modifications
    const onDidSaveDocument = vscode.workspace.onDidSaveTextDocument(async (document) => {
        const relativePath = vscode.workspace.asRelativePath(document.fileName);
        await trackFileActivity(projectRoot, relativePath, 'modified');
    });

    // Diagnostic change handler for error tracking
    const onDidChangeDiagnostics = vscode.languages.onDidChangeDiagnostics(async (event) => {
        for (const uri of event.uris) {
            const diagnostics = vscode.languages.getDiagnostics(uri);
            const errors = diagnostics.filter(d => d.severity === vscode.DiagnosticSeverity.Error);
            
            if (errors.length > 0) {
                // Auto-suggest context for errors
                const config = vscode.workspace.getConfiguration('warRoomContext');
                if (config.get('autoLoadContext')) {
                    const errorMessage = errors[0].message;
                    const context = await loadContext(projectRoot, `error: ${errorMessage}`);
                    
                    if (context && context.suggestions.length > 0) {
                        const action = await vscode.window.showInformationMessage(
                            'Context available for current error',
                            'Show Context'
                        );
                        
                        if (action === 'Show Context') {
                            showContextResult(context);
                        }
                    }
                }
            }
        }
    });

    context.subscriptions.push(
        loadContextCommand,
        searchCodeCommand,
        startSessionCommand,
        showSessionCommand,
        trackErrorCommand,
        onDidOpenTextDocument,
        onDidSaveDocument,
        onDidChangeDiagnostics
    );
}

function findProjectRoot(): string | null {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        return null;
    }

    for (const folder of workspaceFolders) {
        const contextFile = path.join(folder.uri.fsPath, '.context', 'context.yaml');
        if (fs.existsSync(contextFile)) {
            return folder.uri.fsPath;
        }
    }

    return null;
}

async function loadContext(projectRoot: string, query: string): Promise<ContextResult | null> {
    try {
        const scriptPath = path.join(projectRoot, '.context', 'tools', 'context_loader.py');
        const { stdout } = await execAsync(`python3 "${scriptPath}" --query "${query}"`);
        return JSON.parse(stdout);
    } catch (error) {
        console.error('Error loading context:', error);
        vscode.window.showErrorMessage(`Failed to load context: ${error}`);
        return null;
    }
}

async function searchCode(projectRoot: string, query: string): Promise<any[] | null> {
    try {
        const scriptPath = path.join(projectRoot, '.context', 'tools', 'semantic_index.py');
        const { stdout } = await execAsync(`python3 "${scriptPath}" --search "${query}"`);
        return JSON.parse(stdout);
    } catch (error) {
        console.error('Error searching code:', error);
        vscode.window.showErrorMessage(`Failed to search code: ${error}`);
        return null;
    }
}

async function startSession(projectRoot: string, task: string): Promise<SessionContext | null> {
    try {
        const scriptPath = path.join(projectRoot, '.context', 'tools', 'session_manager.py');
        const { stdout } = await execAsync(`python3 "${scriptPath}" --start "${task}"`);
        
        // Get session details
        return await getCurrentSession(projectRoot);
    } catch (error) {
        console.error('Error starting session:', error);
        vscode.window.showErrorMessage(`Failed to start session: ${error}`);
        return null;
    }
}

async function getCurrentSession(projectRoot: string): Promise<SessionContext | null> {
    try {
        const scriptPath = path.join(projectRoot, '.context', 'tools', 'session_manager.py');
        const { stdout } = await execAsync(`python3 "${scriptPath}" --current`);
        const data = JSON.parse(stdout);
        return data.current_session;
    } catch (error) {
        // Session might not exist
        return null;
    }
}

async function trackError(projectRoot: string, errorMessage: string, errorType: string): Promise<void> {
    try {
        const scriptPath = path.join(projectRoot, '.context', 'tools', 'session_manager.py');
        await execAsync(`python3 "${scriptPath}" --track-error "${errorMessage}|${errorType}"`);
    } catch (error) {
        console.error('Error tracking error:', error);
    }
}

async function trackFileActivity(projectRoot: string, filePath: string, activityType: string): Promise<void> {
    try {
        const scriptPath = path.join(projectRoot, '.context', 'tools', 'session_manager.py');
        await execAsync(`python3 "${scriptPath}" --file-activity "${filePath}:${activityType}"`);
    } catch (error) {
        console.error('Error tracking file activity:', error);
    }
}

async function loadCurrentSession(provider: WarRoomContextProvider, projectRoot: string): Promise<void> {
    const session = await getCurrentSession(projectRoot);
    provider.updateSession(session);
}

function showContextResult(context: ContextResult) {
    const panel = vscode.window.createWebviewPanel(
        'warRoomContext',
        'War Room Context',
        vscode.ViewColumn.Beside,
        {}
    );

    panel.webview.html = getContextWebviewContent(context);
}

function showSearchResults(results: any[]) {
    const panel = vscode.window.createWebviewPanel(
        'warRoomSearch',
        'Code Search Results',
        vscode.ViewColumn.Beside,
        {}
    );

    panel.webview.html = getSearchResultsWebviewContent(results);
}

function showSessionDetails(session: SessionContext) {
    const panel = vscode.window.createWebviewPanel(
        'warRoomSession',
        'Development Session',
        vscode.ViewColumn.Beside,
        {}
    );

    panel.webview.html = getSessionWebviewContent(session);
}

function getContextWebviewContent(context: ContextResult): string {
    const suggestions = context.suggestions.map(s => `<li>${s}</li>`).join('');
    const sources = context.context_sources.map(s => `<li>${s.type || 'Unknown'}</li>`).join('');
    const files = context.relevant_files.map(f => `<li>${f.path || f.file_path || 'Unknown'}</li>`).join('');

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>War Room Context</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        h2 { color: #0066cc; }
        ul { padding-left: 20px; }
        .section { margin-bottom: 20px; padding: 15px; background: #f5f5f5; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>Context: ${context.query}</h1>
    
    <div class="section">
        <h2>Suggestions</h2>
        <ul>${suggestions}</ul>
    </div>
    
    <div class="section">
        <h2>Context Sources</h2>
        <ul>${sources}</ul>
    </div>
    
    <div class="section">
        <h2>Relevant Files</h2>
        <ul>${files}</ul>
    </div>
</body>
</html>`;
}

function getSearchResultsWebviewContent(results: any[]): string {
    const resultItems = results.map(r => `
        <div class="result">
            <h3>${r.path}</h3>
            <p><strong>Relevance:</strong> ${(r.relevance * 100).toFixed(1)}%</p>
            <p>${r.excerpt || ''}</p>
        </div>
    `).join('');

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Search Results</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .result { margin-bottom: 20px; padding: 15px; background: #f5f5f5; border-radius: 5px; }
        h3 { margin: 0 0 10px 0; color: #0066cc; }
    </style>
</head>
<body>
    <h1>Code Search Results</h1>
    ${resultItems}
</body>
</html>`;
}

function getSessionWebviewContent(session: SessionContext): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Development Session</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .metric { margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 5px; }
        .quality-good { background: #d4edda; }
        .quality-warning { background: #fff3cd; }
        .quality-danger { background: #f8d7da; }
    </style>
</head>
<body>
    <h1>Session: ${session.session_id}</h1>
    
    <div class="metric">
        <strong>Current Task:</strong> ${session.current_task}
    </div>
    
    <div class="metric">
        <strong>Started:</strong> ${new Date(session.started_at).toLocaleString()}
    </div>
    
    <div class="metric">
        <strong>Last Activity:</strong> ${new Date(session.last_activity).toLocaleString()}
    </div>
    
    <div class="metric">
        <strong>Files Modified:</strong> ${session.files_modified.length}
    </div>
    
    <div class="metric">
        <strong>Error Count:</strong> ${session.error_count}
    </div>
    
    <div class="metric ${session.context_quality > 0.7 ? 'quality-good' : session.context_quality > 0.5 ? 'quality-warning' : 'quality-danger'}">
        <strong>Context Quality:</strong> ${(session.context_quality * 100).toFixed(0)}%
    </div>
</body>
</html>`;
}

export function deactivate() {}