import { ApollonEditor, UMLModel } from '@besser/wme';
import React, { useEffect, useRef, useContext } from 'react';
import styled from 'styled-components';
import { uuid } from '../../utils/uuid';

import { setCreateNewEditor, updateDiagramThunk, selectCreatenewEditor } from '../../services/diagram/diagramSlice';
import { ApollonEditorContext } from './apollon-editor-context';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { selectPreviewedDiagramIndex } from '../../services/version-management/versionManagementSlice';
import { addDiagramToCurrentProject } from '../../utils/localStorage';

const ApollonContainer = styled.div`
  display: flex;
  flex-direction: column;
  flex-grow: 1;
  overflow: hidden;
  width: 100%;
  height: calc(100vh - 60px);
  background-color: var(--apollon-background, #ffffff);
`;

export const ApollonEditorComponent: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<ApollonEditor | null>(null);
  const dispatch = useAppDispatch();
  const { diagram: reduxDiagram } = useAppSelector((state) => state.diagram);
  const options = useAppSelector((state) => state.diagram.editorOptions);
  const createNewEditor = useAppSelector(selectCreatenewEditor);
  const previewedDiagramIndex = useAppSelector(selectPreviewedDiagramIndex);
  const { setEditor } = useContext(ApollonEditorContext);

  // Track if this diagram was added to the project to avoid duplicate additions
  const diagramAddedToProjectRef = useRef<string | null>(null);
  // Hold a payload received before the editor is initialized so we can apply it once ready
  const pendingPayloadRef = useRef<any>(null);
  // Track if we're currently recovering from an error
  const isRecoveringRef = useRef<boolean>(false);

  useEffect(() => {
    let isSubscribed = true;
    // Helper: quick JSON string check
    const isJsonString = (str: string): boolean => {
      try {
        JSON.parse(str);
        return true;
      } catch {
        return false;
      }
    };

    // Helper: Setup model change subscriptions
    const setupModelSubscriptions = (editor: ApollonEditor) => {
      let timeoutId: NodeJS.Timeout;
      editor.subscribeToModelChange((model: UMLModel) => {
        if (!isSubscribed) return;

        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
          if (JSON.stringify(model) !== JSON.stringify(reduxDiagram?.model)) {
            // Check if this is a drag and drop operation (empty diagram becomes non-empty)
            const wasEmpty = !reduxDiagram?.model || !reduxDiagram.model.elements || Object.keys(reduxDiagram.model.elements).length === 0;
            const isNowNonEmpty = model && model.elements && Object.keys(model.elements).length > 0;

            // If diagram went from empty to non-empty, and hasn't been added to project yet, add it
            if (wasEmpty && isNowNonEmpty && reduxDiagram?.id && diagramAddedToProjectRef.current !== reduxDiagram.id) {
              addDiagramToCurrentProject(reduxDiagram.id);
              diagramAddedToProjectRef.current = reduxDiagram.id;
              console.log('Diagram added to project via drag and drop:', reduxDiagram.id);
            }

            try {
              // Send the model as a primitive JSON string to the parent window
              const exported = JSON.stringify(model);
              window.parent.postMessage(exported, '*');
              console.log('Sent diagram JSON to parent');
            } catch (err) {
              console.warn('Failed to send diagram JSON to parent', err);
            }

            dispatch(updateDiagramThunk({
              model,
              lastUpdate: new Date().toISOString()
            }));
          }
        }, 500); // 500ms debounce
      });

      // Also subscribe to discrete changes (immediate events) and forward to parent
      try {
        editor.subscribeToModelDiscreteChange && editor.subscribeToModelDiscreteChange(async () => {
          console.log('Model discrete changed.');
          try {
            const exported = JSON.stringify(editor.model);
            window.parent.postMessage(exported, '*');
            console.log('Sent diagram JSON to parent (discrete)');
          } catch (err) {
            console.warn('Failed to send diagram JSON to parent (discrete)', err);
          }
        });
      } catch (err) {
        // ignore if the editor does not support this API
      }
    };

    // Helper: Recreate editor from scratch when it's in a bad state
    const recreateEditor = async (modelToApply?: any): Promise<boolean> => {
      if (isRecoveringRef.current) {
        console.log('Already recovering editor, skipping duplicate recovery');
        return false;
      }

      isRecoveringRef.current = true;
      console.warn('🔄 Recreating editor due to error state...');

      try {
        if (!containerRef.current) {
          console.error('Container ref is null, cannot recreate editor');
          isRecoveringRef.current = false;
          return false;
        }

        // Destroy existing editor if it exists
        if (editorRef.current) {
          try {
            editorRef.current.destroy();
          } catch (err) {
            console.warn('Error destroying old editor (expected):', err);
          }
          editorRef.current = null;
        }

        // Create new editor
        const newEditor = new ApollonEditor(containerRef.current, options);
        await newEditor.nextRender;
        editorRef.current = newEditor;

        // Apply model if provided
        if (modelToApply) {
          try {
            await newEditor.nextRender;
            newEditor.model = modelToApply;
            console.log('✅ Model applied to recreated editor');
          } catch (err) {
            console.error('Failed to apply model to recreated editor:', err);
          }
        }

        // Re-setup subscriptions
        setupModelSubscriptions(newEditor);
        setEditor!(newEditor);

        // Notify parent window that editor was recovered
        try {
          window.parent.postMessage({ type: 'editor-recovered' }, '*');
        } catch (err) {
          console.warn('Failed to notify parent of recovery', err);
        }

        console.log('✅ Editor successfully recreated');
        isRecoveringRef.current = false;
        return true;
      } catch (err) {
        console.error('Failed to recreate editor:', err);
        isRecoveringRef.current = false;
        return false;
      }
    };

    // Message handler for importing diagram JSON from parent via postMessage
  const onMessage = async (event: MessageEvent) => {
      //console.log('postMessage received (raw):', event.data);

      // Only accept primitive strings (the previous implementation expected text)
      if (Object.prototype.toString.call(event.data) !== '[object String]') {
        console.warn('Ignoring non-string postMessage payload');
        return;
      }

      const text = (event.data as string).trim();
      if (!isJsonString(text)) {
        console.warn('Ignoring non-JSON string payload');
        return;
      }

      let model: any;
      try {
        model = JSON.parse(text);
      } catch (err) {
        console.error('Failed to parse JSON payload:', err);
        return;
      }

      if (!model || typeof model !== 'object' || typeof model.type !== 'string') {
        console.error('Parsed JSON is not a valid diagram model (missing .type):', model);
        return;
      }

      // If editor isn't ready yet, queue the parsed model for later
      if (!editorRef.current) {
        pendingPayloadRef.current = model;
        console.log('Editor not ready yet — queued parsed model');
        return;
      }

      // Ensure Apollon has finished its next render before interacting with its state
      try {
        if (editorRef.current.nextRender) await editorRef.current.nextRender;
      } catch (err) {
        console.warn('Waiting for editor.nextRender failed or timed out', err);
      }

      // Minimal enrichment to avoid internal errors
      model.version = typeof model.version === 'string' ? model.version : '3.0.0';
      model.elements = model.elements || {};
      model.relationships = model.relationships || {};

      try {
        editorRef.current.model = model;
        console.log('Editor model overwritten from incoming message');
      } catch (err) {
        console.error('Failed to set editor.model:', err);
        console.warn('Attempting to recover editor by recreating it...');

        // Try to recover by recreating the editor with the new model
        const recovered = await recreateEditor(model);
        if (!recovered) {
          console.error('❌ Failed to recover editor - user may need to refresh');
        }
      }
    };
  // register listener immediately so we don't miss messages sent before editor is ready
  window.addEventListener('message', onMessage);
    const setupEditor = async () => {
      if (!containerRef.current) return;

      if (createNewEditor || previewedDiagramIndex === -1) {
        // Reset tracking when creating a new editor
        diagramAddedToProjectRef.current = null;
        
        // Initialize or reset editor
        if (editorRef.current) {
          await editorRef.current.nextRender;
          editorRef.current.destroy();
        }
        editorRef.current = new ApollonEditor(containerRef.current, options);
        await editorRef.current.nextRender;

        // Only load the model if we're not changing diagram type
        if (reduxDiagram && reduxDiagram.model && reduxDiagram.model.type === options.type) {
          editorRef.current.model = reduxDiagram.model;
        }

        // If a payload was queued before the editor was ready, apply it now
        if (pendingPayloadRef.current) {
          try {
            if (editorRef.current.nextRender) await editorRef.current.nextRender;
            editorRef.current.model = pendingPayloadRef.current;
            console.log('Applied queued payload to editor.model');
          } catch (err) {
            console.error('Failed to apply queued payload to editor:', err);
          }
          pendingPayloadRef.current = null;
        }

        // Setup model change subscriptions
        setupModelSubscriptions(editorRef.current);

        setEditor!(editorRef.current);
        dispatch(setCreateNewEditor(false));
      } else if (previewedDiagramIndex !== -1 && editorRef.current) {
        // Handle preview mode
        const editorOptions = { ...options, readonly: true };
        await editorRef.current.nextRender;
        editorRef.current.destroy();
        editorRef.current = new ApollonEditor(containerRef.current, editorOptions);
        await editorRef.current.nextRender;

        const modelToPreview = reduxDiagram?.versions && reduxDiagram.versions[previewedDiagramIndex]?.model;
        if (modelToPreview) {
          editorRef.current.model = modelToPreview;
        }
        // If a payload was queued before the editor was ready, apply it now (preview branch)
        if (pendingPayloadRef.current) {
          try {
            if (editorRef.current.nextRender) await editorRef.current.nextRender;
            editorRef.current.model = pendingPayloadRef.current;
            console.log('Applied queued payload to editor.model (preview)');
          } catch (err) {
            console.error('Failed to apply queued payload to editor (preview):', err);
          }
          pendingPayloadRef.current = null;
        }
      }
    };

    setupEditor();

    // ====================
    // DEBUG/TESTING FUNCTIONS - Expose to window for testing
    // ====================
    if (typeof window !== 'undefined') {
      (window as any).apollonDebug = {
        // Force destroy the editor to simulate the error
        forceDestroy: () => {
          console.warn('🔴 FORCE DESTROYING EDITOR (for testing)');
          if (editorRef.current) {
            try {
              editorRef.current.destroy();
              console.log('Editor destroyed successfully');
            } catch (err) {
              console.error('Error during force destroy:', err);
            }
          } else {
            console.warn('No editor to destroy');
          }
        },

        // Get current editor state
        getEditorState: () => {
          if (!editorRef.current) {
            return { status: 'NO_EDITOR', message: 'Editor ref is null' };
          }
          try {
            // Try to access the model to see if editor is responsive
            const model = editorRef.current.model;
            return {
              status: 'HEALTHY',
              message: 'Editor is responsive',
              hasModel: !!model,
              elementCount: model?.elements ? Object.keys(model.elements).length : 0
            };
          } catch (err) {
            return {
              status: 'ERROR',
              message: 'Editor exists but is unresponsive',
              error: String(err)
            };
          }
        },

        // Manually trigger recovery
        triggerRecovery: async (testModel?: any) => {
          console.log('🔧 Manually triggering recovery...');
          const result = await recreateEditor(testModel);
          console.log('Recovery result:', result ? '✅ Success' : '❌ Failed');
          return result;
        },

        // Simulate receiving a message (for testing)
        simulateMessage: (jsonString: string) => {
          console.log('📨 Simulating postMessage with:', jsonString.substring(0, 100) + '...');
          window.postMessage(jsonString, '*');
        },

        // Check if currently recovering
        isRecovering: () => isRecoveringRef.current
      };

      // Debug tools are available via window.apollonDebug
      // Uncomment below to see available commands on load:
      // console.log('🛠️ Apollo Debug Tools Available:');
      // console.log('  • window.apollonDebug.forceDestroy() - Force destroy editor');
      // console.log('  • window.apollonDebug.getEditorState() - Check editor health');
      // console.log('  • window.apollonDebug.triggerRecovery() - Manually trigger recovery');
      // console.log('  • window.apollonDebug.simulateMessage(json) - Simulate incoming message');
      // console.log('  • window.apollonDebug.isRecovering() - Check if recovery is in progress');
    }

    return () => {
      isSubscribed = false;
      window.removeEventListener('message', onMessage);
      // Clean up debug tools
      if (typeof window !== 'undefined') {
        delete (window as any).apollonDebug;
      }
    };
  }, [createNewEditor, previewedDiagramIndex, options.type]);

  const key = reduxDiagram?.id || uuid();

  return <ApollonContainer key={key} ref={containerRef} />;
};
