import unittest
import numpy as np
from mpips.dag.control_flow import PipelinePlan, evaluate_condition, parse_condition


def node(id, type, **parameters):
    return {'id': id, 'type': type, 'parameters': parameters}


def edge(source, target, source_handle='output_image', target_handle='input_image'):
    return dict(source=source,target=target,source_handle=source_handle,target_handle=target_handle)


def loop_graph(condition='iteration >= 3', limit=10, mode='latest'):
    nodes=[node('in','input'),node('loop','loop',max_iterations=limit,result_mode=mode,score_metric='mean',score_direction='maximize'),node('step','add'),node('gate','condition',condition=condition),node('out','output')]
    edges=[edge('in','loop'),edge('loop','step','current_image'),edge('step','gate'),edge('gate','loop','true_image','stop_image'),edge('gate','loop','false_image','feedback_image'),edge('loop','out')]
    return nodes,edges


def simulate(nodes, edges, seed=0, transform=None):
    plan=PipelinePlan(nodes,edges); context={}; refs={}; calls=[]; result=None
    for n in plan.steps(context,refs):
        calls.append(n['id'])
        values={e['target_handle']:context[(e['source'],e['source_handle'])] for e in plan.current_edges}
        if n['type']=='input': value=np.full((4,4),seed,dtype=np.float64)
        elif n['type']=='output': result=values['input_image']; value=result
        else: value=(transform(values['input_image']) if transform else values['input_image']+1)
        context[(n['id'],'output_image')]=value
        refs[(n['id'],'output_image')]=('in','output_image')
    return result,calls,plan.events,context,refs


class Conditions(unittest.TestCase):
    def test_comparisons_and_boolean_logic(self):
        self.assertTrue(evaluate_condition('iteration >= 3 and (mean > 2 or value == 0)',{'iteration':3,'mean':3,'value':2}))
        self.assertFalse(evaluate_condition('not (iteration % 2 == 0)',{'iteration':2}))
    def test_rejects_code_and_unknown_names(self):
        for text in ["__import__('os')",'mean.real > 0','value[0]','[x for x in mean]','unknown == 1','mean ** 999','1 / 0 > 0','x'*513]:
            with self.subTest(text=text),self.assertRaises(ValueError): evaluate_condition(text,{'mean':2,'value':3})
    def test_validation_matches_public_expression_grammar(self):
        for text in ['mean', '2', 'mean > not std', '0x10 > 2', 'mean # comment', '1_000 > 2', ' + '.join(['1'] * 40) + ' > 0']:
            with self.subTest(text=text), self.assertRaises(ValueError): parse_condition(text)
        self.assertTrue(evaluate_condition('  iteration >= 3  ', {'iteration': 3}))

    def test_short_circuit_guard_for_previous_values(self):
        self.assertFalse(evaluate_condition('iteration > 1 and previous_value > 0',{'iteration':1}))
        with self.assertRaises(ValueError):evaluate_condition('previous_value > 0',{'iteration':1})


class Pipelines(unittest.TestCase):
    def test_old_acyclic_pipeline(self):
        result,calls,*_=simulate([node('in','input'),node('x','add'),node('out','output')],[edge('in','x'),edge('x','out')])
        self.assertEqual(float(result.mean()),1);self.assertEqual(calls,['in','x','out'])
    def test_true_false_and_exclusive_join(self):
        for condition,expected,active in [('mean >= 0',1,'yes'),('mean < 0',1,'no')]:
            ns=[node('in','input'),node('gate','condition',condition=condition),node('yes','add'),node('no','add'),node('join','branch_merge'),node('out','output')]
            es=[edge('in','gate'),edge('gate','yes','true_image'),edge('gate','no','false_image'),edge('yes','join',target_handle='true_image'),edge('no','join',target_handle='false_image'),edge('join','out')]
            result,calls,*_=simulate(ns,es)
            self.assertEqual(float(result.mean()),expected);self.assertIn(active,calls);self.assertNotIn('no' if active=='yes' else 'yes',calls)
    def test_merge_receives_only_active_inputs(self):
        ns=[node('in','input'),node('gate','condition',condition='True'),node('join','branch_merge'),node('out','output')]
        es=[edge('in','gate'),edge('gate','join','true_image','true_image'),edge('gate','join','false_image','false_image'),edge('join','out')]
        result,*_=simulate(ns,es);self.assertEqual(float(result.mean()),0)
    def test_loop_stops_on_condition(self):
        ns,es=loop_graph(); result,calls,events,_,refs=simulate(ns,es)
        self.assertEqual(float(result.mean()),3);self.assertEqual(calls.count('step'),3)
        self.assertEqual(events[-1]['stop_reason'],'condition');self.assertEqual(events[-1]['iterations'],3)
        self.assertEqual(refs[('loop','output_image')],('in','output_image'))
    def test_loop_hard_limit(self):
        ns,es=loop_graph('False',4);result,_,events,*_=simulate(ns,es)
        self.assertEqual(float(result.mean()),4);self.assertEqual(events[-1]['stop_reason'],'iteration_limit')
    def test_loop_best_result_is_copied(self):
        ns,es=loop_graph('False',4,'best')
        values=iter([4,8,3,1]); result,*_=simulate(ns,es,transform=lambda image: np.full_like(image,next(values)))
        self.assertEqual(float(result.mean()),8)
    def test_delta_stopping_and_run_isolation(self):
        ns,es=loop_graph('iteration > 1 and delta_mean < 0.1',8)
        for _ in range(2):
            values=iter([1,1.05]); result,calls,events,*_=simulate(ns,es,transform=lambda image:np.full_like(image,next(values)))
            self.assertEqual(calls.count('step'),2);self.assertEqual(events[-1]['iterations'],2)
    def test_sequential_loops(self):
        ns, es = loop_graph('False', 2)
        ns += [node('loop2','loop',max_iterations=3),node('step2','add')]
        es = [e for e in es if e['target'] != 'out'] + [edge('loop','loop2'),edge('loop2','step2','current_image'),edge('step2','loop2',target_handle='feedback_image'),edge('loop2','out')]
        result, calls, events, *_ = simulate(ns, es)
        self.assertEqual(float(result.mean()), 5)
        self.assertEqual(calls.count('step'), 2)
        self.assertEqual(calls.count('step2'), 3)
        self.assertEqual([event['iterations'] for event in events if 'iterations' in event], [2,3])

    def test_loop_branches_do_not_reuse_previous_outputs(self):
        ns, es = loop_graph()
        ns += [node('choose','condition',condition='iteration % 2 == 1'),node('alternate','add'),node('join','branch_merge')]
        es = [e for e in es if e['source'] != 'step' and not (e['source']=='loop' and e['target']=='step')]
        es += [edge('loop','choose','current_image'),edge('choose','step','true_image'),edge('choose','alternate','false_image'),edge('step','join',target_handle='true_image'),edge('alternate','join',target_handle='false_image'),edge('join','gate')]
        result, calls, *_ = simulate(ns, es)
        self.assertEqual(float(result.mean()), 3)
        self.assertEqual(calls.count('step'), 2)
        self.assertEqual(calls.count('alternate'), 1)

    def test_rejects_excessive_work(self):
        ns, es = loop_graph('False', 100)
        ns += [node('extra'+str(i),'add') for i in range(100)]
        es = [e for e in es if not (e['source']=='step' and e['target']=='gate')]
        es += [edge('step','extra0')] + [edge('extra'+str(i),'extra'+str(i+1)) for i in range(99)] + [edge('extra99','gate')]
        with self.assertRaisesRegex(ValueError, '10000'): PipelinePlan(ns, es)

    def test_rejects_ambiguous_loop_return(self):
        ns, es = loop_graph()
        es = [e for e in es if e['target_handle'] != 'stop_image'] + [edge('step','loop',target_handle='stop_image')]
        with self.assertRaisesRegex(ValueError, 'exactly one active'): simulate(ns, es)

    def test_rejects_undeclared_cycles(self):
        with self.assertRaises(ValueError):PipelinePlan([node('a','add'),node('b','add')],[edge('a','b'),edge('b','a')])
    def test_rejects_invalid_loop_boundaries(self):
        for scenario in ['missing_seed','invalid_limit','external_return','leak_output','nested','expression']:
            ns,es=loop_graph()
            if scenario=='missing_seed':es=es[1:]
            elif scenario=='invalid_limit':ns[1]['parameters']['max_iterations']=0
            elif scenario=='external_return':es[-2]=edge('in','loop','output_image','feedback_image')
            elif scenario=='leak_output':es.append(edge('step','out'))
            elif scenario=='nested':ns[2]['type']='loop'
            else:ns[3]['parameters']['condition']='__import__("os")'
            with self.subTest(scenario=scenario),self.assertRaises(ValueError):PipelinePlan(ns,es)
    def test_rejects_ambiguous_branch_merge(self):
        ns=[node('in','input'),node('join','branch_merge'),node('out','output')]
        es=[edge('in','join',target_handle='true_image'),edge('in','join',target_handle='false_image'),edge('join','out')]
        with self.assertRaises(ValueError):simulate(ns,es)


class Contracts(unittest.TestCase):
    def test_shared_graph_contract(self):
        import json
        from pathlib import Path
        fixtures=json.loads(Path(__file__).with_name("pipeline-control-flow.json").read_text())
        for fixture in fixtures:
            graph=fixture["graph"]
            with self.subTest(name=fixture["name"]):
                if fixture["valid"]: PipelinePlan(graph["nodes"],graph["edges"])
                else:
                    with self.assertRaises(ValueError):PipelinePlan(graph["nodes"],graph["edges"])


class ExecutorIntegration(unittest.TestCase):
    def execute(self, graph, cancel=False):
        import cv2
        import os
        from mpips.dag.executor import DAGExecutor
        class MemoryStorage:
            def __init__(self): self.uploads=[];self.paths=[]
            def download_image(self,source,local_path,**kwargs):
                self.paths.append(local_path)
                image=(np.arange(32*32).reshape(32,32)%16+20).astype(np.uint8)
                cv2.imwrite(local_path,image)
            def upload_image(self,local_path,target,**kwargs):
                self.paths.append(local_path);self.uploads.append(cv2.imread(local_path,cv2.IMREAD_UNCHANGED))
        storage=MemoryStorage();progress=[]
        def callback(id,value):
            progress.append((id,value))
            if cancel and id=='gate':raise RuntimeError('cancelled')
        executor=DAGExecutor(storage=storage)
        if cancel:
            with self.assertRaises(RuntimeError):executor.execute(graph,{'in':{'key':'source.png'}},{'prefix':'test/'},callback)
            self.assertTrue(all(not os.path.exists(path) for path in storage.paths))
            return
        result=executor.execute(graph,{'in':{'key':'source.png'}},{'prefix':'test/'},callback)
        self.assertTrue(all(not os.path.exists(path) for path in storage.paths))
        self.assertTrue(all(progress[i][1]<=progress[i+1][1] for i in range(len(progress)-1)))
        self.assertEqual(result['status'],'completed');self.assertEqual(len(storage.uploads),1)
        self.assertIn('before',result['outputs']['out']['quality_assessment'])
        return result,storage.uploads[0]
    def graph(self):
        ns,es=loop_graph('iteration >= 3',5)
        ns[2]['type']='brightness_contrast';ns[2]['parameters']={'alpha':1,'beta':10}
        return {'nodes':ns,'edges':es}
    def test_real_processor_loop_uploads_only_final_result(self):
        result,image=self.execute(self.graph())
        self.assertAlmostEqual(float(image.mean()),57.5)
        self.assertEqual(result['control_flow'][-1]['iterations'],3)
        self.assertEqual(result['outputs']['out']['control_flow'][-1]['stop_reason'],'condition')
    def test_real_processor_hard_limit(self):
        graph = self.graph()
        graph['nodes'][3]['parameters']['condition'] = 'False'
        result, image = self.execute(graph)
        self.assertAlmostEqual(float(image.mean()), 77.5)
        self.assertEqual(result['control_flow'][-1]['stop_reason'], 'iteration_limit')

    def test_real_branches_and_join(self):
        for condition, expected in [('True',37.5),('False',47.5)]:
            ns=[node('in','input'),node('gate','condition',condition=condition),node('yes','brightness_contrast',beta=10),node('no','brightness_contrast',beta=20),node('join','branch_merge'),node('out','output')]
            es=[edge('in','gate'),edge('gate','yes','true_image'),edge('gate','no','false_image'),edge('yes','join',target_handle='true_image'),edge('no','join',target_handle='false_image'),edge('join','out')]
            result, image = self.execute({'nodes':ns,'edges':es})
            self.assertAlmostEqual(float(image.mean()), expected)
            self.assertEqual(result['control_flow'][0]['branch'], condition.lower())

    def test_real_best_result_selects_earlier_image(self):
        graph=self.graph();graph['nodes'][1]['parameters'].update(result_mode='best',score_metric='mean',score_direction='minimize')
        _,image=self.execute(graph);self.assertAlmostEqual(float(image.mean()),37.5)
    def test_cancellation_retains_temporary_file_cleanup(self):
        self.execute(self.graph(),cancel=True)
    def test_real_legacy_pipeline_has_unchanged_result_shape(self):
        graph={'nodes':[node('in','input'),node('step','brightness_contrast',beta=10),node('out','output')], 'edges':[edge('in','step'),edge('step','out')]}
        result,image=self.execute(graph)
        self.assertNotIn('control_flow',result);self.assertAlmostEqual(float(image.mean()),37.5)


if __name__=='__main__':unittest.main()
